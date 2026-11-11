/**
 * DES.ai.N UXP bridge client.
 *
 * Connects to the MCP process WebSocket hub and executes Photoshop DOM /
 * batchPlay commands. UXP can only act as a WebSocket client, so the Python
 * side hosts the server.
 */
const { app, action, core } = require("photoshop");
const { storage } = require("uxp");
const fs = storage.localFileSystem;

const PROTOCOL = 1;
const PLUGIN_VERSION = "0.2.0";

let socket = null;
let intentionalClose = false;
let reconnectAttempt = 0;
let reconnectTimer = null;

const statusEl = document.getElementById("status");
const urlEl = document.getElementById("url");
const connectBtn = document.getElementById("connectBtn");
const disconnectBtn = document.getElementById("disconnectBtn");

function setStatus(text, kind) {
  statusEl.textContent = text;
  statusEl.className = kind || "";
}

function photoshopVersion() {
  try {
    return String(app.version || "unknown");
  } catch (e) {
    return "unknown";
  }
}

function activeDoc() {
  if (!app.documents.length) {
    throw Object.assign(new Error("No active document."), { code: "NO_DOCUMENT" });
  }
  return app.activeDocument;
}

function layerBounds(layer) {
  const b = layer.bounds;
  const left = Math.round(b.left);
  const top = Math.round(b.top);
  const right = Math.round(b.right);
  const bottom = Math.round(b.bottom);
  const width = right - left;
  const height = bottom - top;
  return {
    left,
    top,
    right,
    bottom,
    width,
    height,
    center_x: left + Math.floor(width / 2),
    center_y: top + Math.floor(height / 2),
  };
}

function flattenLayers(container, out) {
  for (const layer of container.layers) {
    out.push(layer);
    if (layer.layers && layer.layers.length) {
      flattenLayers(layer, out);
    }
  }
  return out;
}

function allLayers(doc) {
  return flattenLayers(doc, []);
}

function getLayerByIndex(index) {
  const layers = allLayers(activeDoc());
  if (index < 0 || index >= layers.length) {
    throw Object.assign(new Error(`Layer index ${index} out of bounds.`), {
      code: "LAYER_INDEX",
    });
  }
  return layers[index];
}

function hexToRgb(hex) {
  let c = String(hex || "").replace("#", "").trim();
  if (c.length === 3) c = c[0] + c[0] + c[1] + c[1] + c[2] + c[2];
  const n = parseInt(c.slice(0, 6), 16);
  if (Number.isNaN(n)) return { r: 255, g: 255, b: 255 };
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
}

async function withCheckpoint(checkpoint, fn) {
  if (checkpoint) {
    try {
      await historyCheckpoint();
    } catch (e) {
      // Non-fatal: continue the operation.
    }
  }
  return fn();
}

async function historyCheckpoint() {
  await action.batchPlay(
    [
      {
        _obj: "make",
        _target: [{ _ref: "snapshotClass" }],
        from: { _ref: "historyState", _enum: "ordinal", _value: "targetEnum" },
        name: "DESAIN_CHECKPOINT",
      },
    ],
    { synchronousExecution: true }
  );
  return { message: "History checkpoint created." };
}

async function historyUndo() {
  await action.batchPlay(
    [{ _obj: "select", _target: [{ _ref: "historyState", _offset: -1 }] }],
    { synchronousExecution: true }
  );
  return { message: "Undo executed." };
}

async function createDocument(params) {
  const width = params.width || 1080;
  const height = params.height || 1080;
  const name = params.filename || params.name || "Untitled";
  await app.createDocument({
    width,
    height,
    resolution: 72,
    mode: "RGBColorMode",
    fill: "transparent",
    name,
  });
  return {
    message: `Canvas created successfully. Resolution: ${width}x${height}.`,
    width,
    height,
  };
}

async function openDocument(params) {
  if (!params.path) throw new Error("path is required");
  const file = await fs.getEntryWithUrl("file:" + params.path.replace(/\\/g, "/"));
  await app.open(file);
  return { message: "Document opened successfully.", path: params.path };
}

async function closeDocument() {
  const doc = activeDoc();
  await doc.closeWithoutSaving();
  return { message: "Document closed without saving." };
}

async function exportPng(params) {
  const doc = activeDoc();
  const path = params.path;
  if (!path) throw new Error("path is required");
  const file = await fs.createEntryWithUrl("file:" + path.replace(/\\/g, "/"), {
    overwrite: true,
  });
  await doc.saveAs.png(file, { compression: 6 }, true);
  return { message: "Preview exported.", path };
}

async function saveDocument(params) {
  const filename = params.filename || "saved_design";
  const outputFolder = (params.output_folder || ".").replace(/\\/g, "/");
  const pngPath = `${outputFolder.replace(/\/$/, "")}/${filename}.png`;
  await exportPng({ path: pngPath });
  if (params.save_psd) {
    const doc = activeDoc();
    const forcePsb =
      doc.width > 30000 ||
      doc.height > 30000 ||
      String(doc.name || "").toLowerCase().endsWith(".psb");
    const ext = forcePsb ? ".psb" : ".psd";
    const srcPath = `${outputFolder.replace(/\/$/, "")}/${filename}${ext}`;
    const file = await fs.createEntryWithUrl("file:" + srcPath, { overwrite: true });
    if (forcePsb) {
      await doc.saveAs.psb(file, {}, true);
    } else {
      await doc.saveAs.psd(file, {}, true);
    }
  }
  return {
    message: `Saved as ${filename}.png (document still open for further edits).`,
    filename,
  };
}

async function getLayerContext() {
  const doc = activeDoc();
  const layers = allLayers(doc);
  const fonts = new Set();
  const out = [];
  for (let i = 0; i < layers.length; i++) {
    const layer = layers[i];
    const info = {
      index: i,
      name: layer.name,
      visible: !!layer.visible,
      opacity: Math.round(Number(layer.opacity ?? 100)),
      blend_mode: String(layer.blendMode || "normal"),
      kind: layer.kind ? String(layer.kind) : "unknown",
      bounds: layerBounds(layer),
    };
    if (layer.kind === "text" || layer.textItem) {
      try {
        const ti = layer.textItem;
        info.kind = "text";
        info.text = ti.contents;
        info.font = ti.characterStyle && ti.characterStyle.fontName;
        info.font_size = ti.characterStyle && ti.characterStyle.size;
        if (info.font) fonts.add(info.font);
        if (ti.characterStyle && ti.characterStyle.color) {
          const c = ti.characterStyle.color.rgb;
          const hex = `#${[c.red, c.green, c.blue]
            .map((v) => Math.round(v).toString(16).padStart(2, "0"))
            .join("")}`;
          info.color_hex = hex;
        }
      } catch (e) {
        info.kind = "text";
      }
    }
    out.push(info);
  }
  return {
    resolution: `${Math.round(doc.width)}x${Math.round(doc.height)}`,
    canvas_w: Math.round(doc.width),
    canvas_h: Math.round(doc.height),
    layers: out,
    fonts_used: Array.from(fonts).sort(),
  };
}

async function addTextLayer(params) {
  const doc = activeDoc();
  const rgb = hexToRgb(params.hex_color || "#FFFFFF");
  const layer = await doc.createTextLayer({
    contents: params.content || "Text",
    fontSize: params.font_size || 72,
    fontColor: { rgb: { red: rgb.r, green: rgb.g, blue: rgb.b } },
    position: { x: params.x || 0, y: params.y || 0 },
  });
  if (params.font_name && layer.textItem && layer.textItem.characterStyle) {
    try {
      layer.textItem.characterStyle.fontName = params.font_name;
    } catch (e) {}
  }
  if (params.opacity != null) layer.opacity = params.opacity;
  if (params.rotation) {
    await layer.rotate(params.rotation, constantsAnchor());
  }
  const layers = allLayers(doc);
  const index = layers.indexOf(layer);
  return {
    message: `Text layer added successfully at index ${index}.`,
    index,
    bounds: layerBounds(layer),
  };
}

function constantsAnchor() {
  // UXP rotate uses AnchorPosition when available.
  try {
    const { constants } = require("photoshop");
    return constants.AnchorPosition.MIDDLECENTER;
  } catch (e) {
    return undefined;
  }
}

async function setLayerProperties(params) {
  const layer = getLayerByIndex(params.index);
  if (params.text != null && layer.textItem) layer.textItem.contents = params.text;
  if (params.font_size != null && layer.textItem && layer.textItem.characterStyle) {
    layer.textItem.characterStyle.size = params.font_size;
  }
  if (params.font_name != null && layer.textItem && layer.textItem.characterStyle) {
    layer.textItem.characterStyle.fontName = params.font_name;
  }
  if (params.hex_color != null && layer.textItem && layer.textItem.characterStyle) {
    const rgb = hexToRgb(params.hex_color);
    layer.textItem.characterStyle.color = {
      rgb: { red: rgb.r, green: rgb.g, blue: rgb.b },
    };
  }
  if (params.opacity != null) layer.opacity = params.opacity;
  return {
    message: `Layer ${params.index} properties updated.`,
    bounds: layerBounds(layer),
  };
}

async function moveLayer(params) {
  const layer = getLayerByIndex(params.index);
  await layer.translate(params.delta_x || 0, params.delta_y || 0);
  return {
    message: `Layer ${params.index} moved by (${params.delta_x || 0},${params.delta_y || 0}).`,
    bounds: layerBounds(layer),
  };
}

async function rotateLayer(params) {
  const layer = getLayerByIndex(params.index);
  await layer.rotate(params.angle || 0, constantsAnchor());
  return { message: `Layer ${params.index} rotated by ${params.angle || 0}°.`, bounds: layerBounds(layer) };
}

async function scaleLayer(params) {
  const layer = getLayerByIndex(params.index);
  const s = params.scale_percent || 100;
  await layer.scale(s, s, constantsAnchor());
  return { message: `Layer ${params.index} scaled to ${s}%.`, bounds: layerBounds(layer) };
}

async function reorderLayer(params) {
  const doc = activeDoc();
  const layers = allLayers(doc);
  const src = layers[params.index];
  const tgt = layers[params.new_index];
  if (!src || !tgt) throw new Error("Layer index out of bounds.");
  if (params.new_index < params.index) {
    await src.moveAbove(tgt);
  } else {
    await src.moveBelow(tgt);
  }
  return { message: `Layer moved from index ${params.index} to ${params.new_index}.` };
}

async function addSolidColorLayer(params) {
  const doc = activeDoc();
  const rgb = hexToRgb(params.hex_color || "#000000");
  const layer = await doc.createLayer({ name: `Color Fill ${params.hex_color || "#000000"}` });
  await action.batchPlay(
    [
      {
        _obj: "fill",
        using: { _enum: "fillContents", _value: "color" },
        color: {
          _obj: "RGBColor",
          red: rgb.r,
          grain: rgb.g,
          blue: rgb.b,
        },
        opacity: { _unit: "percentUnit", _value: 100 },
      },
    ],
    { synchronousExecution: true }
  );
  if (params.opacity != null) layer.opacity = params.opacity;
  const index = allLayers(doc).indexOf(layer);
  return { message: `Solid color layer added successfully at index ${index}.`, index };
}

async function addGradientLayer(params) {
  // Approximate with solid + note; full gradient via batchPlay descriptors.
  const rgb1 = hexToRgb(params.hex_color1 || "#000000");
  const rgb2 = hexToRgb(params.hex_color2 || "#333333");
  const doc = activeDoc();
  const layer = await doc.createLayer({ name: "Gradient" });
  await action.batchPlay(
    [
      {
        _obj: "gradientEventEnum",
        from: {
          _obj: "paint",
          horizontal: { _unit: "pixelsUnit", _value: 0 },
          vertical: { _unit: "pixelsUnit", _value: 0 },
        },
        to: {
          _obj: "paint",
          horizontal: { _unit: "pixelsUnit", _value: doc.width },
          vertical: { _unit: "pixelsUnit", _value: doc.height },
        },
        type: { _enum: "gradientType", _value: "linear" },
        gradient: {
          _obj: "gradientClassEvent",
          name: "Custom",
          gradientForm: { _enum: "gradientForm", _value: "customStops" },
          interfaceIconFrameDimmed: 4096,
          colors: [
            {
              _obj: "colorStop",
              color: { _obj: "RGBColor", red: rgb1.r, grain: rgb1.g, blue: rgb1.b },
              type: { _enum: "colorStopType", _value: "userStop" },
              location: 0,
              midpoint: 50,
            },
            {
              _obj: "colorStop",
              color: { _obj: "RGBColor", red: rgb2.r, grain: rgb2.g, blue: rgb2.b },
              type: { _enum: "colorStopType", _value: "userStop" },
              location: 4096,
              midpoint: 50,
            },
          ],
        },
      },
    ],
    { synchronousExecution: true }
  );
  if (params.opacity != null) layer.opacity = params.opacity;
  const index = allLayers(doc).indexOf(layer);
  return { message: `Gradient layer added successfully at index ${index}.`, index };
}

async function addShape(params) {
  const rgb = hexToRgb(params.hex_color || "#FFFFFF");
  const x = params.x || 0;
  const y = params.y || 0;
  const w = params.width || 100;
  const h = params.height || 100;
  const shapeType = params.shape_type === "ellipse" || params.shape_type === "circle" ? "ellipse" : "rectangle";
  const unitRect = {
    _obj: shapeType,
    top: { _unit: "pixelsUnit", _value: y },
    left: { _unit: "pixelsUnit", _value: x },
    bottom: { _unit: "pixelsUnit", _value: y + h },
    right: { _unit: "pixelsUnit", _value: x + w },
  };
  if (shapeType === "rectangle") {
    const r = params.corner_radius || 0;
    unitRect.topLeft = { _unit: "pixelsUnit", _value: r };
    unitRect.topRight = { _unit: "pixelsUnit", _value: r };
    unitRect.bottomLeft = { _unit: "pixelsUnit", _value: r };
    unitRect.bottomRight = { _unit: "pixelsUnit", _value: r };
  }
  await action.batchPlay(
    [
      {
        _obj: "make",
        _target: [{ _ref: "contentLayer" }],
        using: {
          _obj: "contentLayer",
          type: {
            _obj: "solidColorLayer",
            color: { _obj: "RGBColor", red: rgb.r, grain: rgb.g, blue: rgb.b },
          },
          shape: unitRect,
        },
      },
    ],
    { synchronousExecution: true }
  );
  const doc = activeDoc();
  const layer = doc.activeLayers[0];
  if (params.opacity != null) layer.opacity = params.opacity;
  if (params.rotation) await layer.rotate(params.rotation, constantsAnchor());
  const index = allLayers(doc).indexOf(layer);
  return {
    message: `Shape (${params.shape_type || "rectangle"}) added successfully at index ${index}.`,
    index,
    bounds: layerBounds(layer),
  };
}

async function changeShapeColor(params) {
  const layer = getLayerByIndex(params.index);
  app.activeDocument.activeLayers = [layer];
  const rgb = hexToRgb(params.hex_color || "#FFFFFF");
  await action.batchPlay(
    [
      {
        _obj: "set",
        _target: [{ _ref: "contentLayer", _enum: "ordinal", _value: "targetEnum" }],
        to: {
          _obj: "solidColorLayer",
          color: { _obj: "RGBColor", red: rgb.r, grain: rgb.g, blue: rgb.b },
        },
      },
    ],
    { synchronousExecution: true }
  );
  return { message: `Shape layer ${params.index} colour changed to ${params.hex_color}.` };
}

async function addStroke(params) {
  const layer = getLayerByIndex(params.index);
  app.activeDocument.activeLayers = [layer];
  const rgb = hexToRgb(params.hex_color || "#FFFFFF");
  await action.batchPlay(
    [
      {
        _obj: "set",
        _target: [
          { _ref: "property", _property: "layerEffects" },
          { _ref: "layer", _enum: "ordinal", _value: "targetEnum" },
        ],
        to: {
          _obj: "layerEffects",
          frameFX: {
            _obj: "frameFX",
            enabled: true,
            style: { _enum: "frameStyle", _value: "outsetFrame" },
            paintType: { _enum: "frameFill", _value: "solidColor" },
            size: { _unit: "pixelsUnit", _value: params.thickness || 2 },
            opacity: { _unit: "percentUnit", _value: 100 },
            color: { _obj: "RGBColor", red: rgb.r, grain: rgb.g, blue: rgb.b },
          },
        },
      },
    ],
    { synchronousExecution: true }
  );
  return { message: `Stroke (${params.thickness || 2}px, ${params.hex_color}) added to layer ${params.index}.` };
}

async function placeImage(path, opts) {
  if (!path) throw new Error("path is required");
  const file = await fs.getEntryWithUrl("file:" + String(path).replace(/\\/g, "/"));
  const doc = activeDoc();
  // Place as embedded / open-copy paste fallback via batchPlay placeEvent.
  await action.batchPlay(
    [
      {
        _obj: "placeEvent",
        null: { _path: file, _kind: "local" },
        freeTransformCenterState: {
          _enum: "quadCenterState",
          _value: "QCSAverage",
        },
        offset: {
          _obj: "offset",
          horizontal: { _unit: "pixelsUnit", _value: 0 },
          vertical: { _unit: "pixelsUnit", _value: 0 },
        },
      },
    ],
    { synchronousExecution: true }
  );
  const layer = doc.activeLayers[0];
  if (opts && opts.opacity != null) layer.opacity = opts.opacity;
  if (opts && opts.x != null && opts.y != null) {
    const b = layerBounds(layer);
    await layer.translate(opts.x - b.left, opts.y - b.top);
  }
  if (opts && opts.width && opts.height) {
    const b = layerBounds(layer);
    if (b.width > 0 && b.height > 0) {
      const scale = Math.min(opts.width / b.width, opts.height / b.height) * 100;
      await layer.scale(scale, scale, constantsAnchor());
    }
  }
  if (opts && opts.rotation) await layer.rotate(opts.rotation, constantsAnchor());
  if (opts && opts.remove_background) {
    await selectSubjectAndMaskOnActive();
  }
  const index = allLayers(doc).indexOf(layer);
  return { layer, index, bounds: layerBounds(layer) };
}

async function addImageLayer(params) {
  const placed = await placeImage(params.path, {
    opacity: params.opacity,
  });
  // Scale to canvas.
  const doc = activeDoc();
  const b = placed.bounds;
  if (b.width > 0 && b.height > 0) {
    const scale = Math.max(doc.width / b.width, doc.height / b.height) * 100;
    await placed.layer.scale(scale, scale, constantsAnchor());
  }
  return {
    message: `Image layer added successfully at index ${placed.index}.`,
    index: placed.index,
    bounds: layerBounds(placed.layer),
  };
}

async function addElementLayer(params) {
  const placed = await placeImage(params.path, params);
  return {
    message: `Element image placed at (${params.x},${params.y}), size ${params.width}x${params.height}.`,
    index: placed.index,
    bounds: placed.bounds,
  };
}

async function selectSubjectAndMaskOnActive() {
  await action.batchPlay(
    [
      {
        _obj: "autoCutout",
        sampleAllLayers: false,
      },
    ],
    { synchronousExecution: true }
  ).catch(async () => {
    await action.batchPlay(
      [{ _obj: "selectSubject", sampleAllLayers: false }],
      { synchronousExecution: true }
    );
  });
  await action.batchPlay(
    [
      {
        _obj: "make",
        new: { _class: "channel" },
        at: { _ref: "channel", _enum: "channel", _value: "mask" },
        using: { _enum: "userMaskEnabled", _value: "revealSelection" },
      },
    ],
    { synchronousExecution: true }
  );
}

async function selectSubjectAndMask(params) {
  const layer = getLayerByIndex(params.index);
  app.activeDocument.activeLayers = [layer];
  await selectSubjectAndMaskOnActive();
  return { message: `Subject selected and mask applied to layer ${params.index}.` };
}

async function addPillCta(params) {
  const height = params.height || 120;
  const corner = params.corner_radius != null ? params.corner_radius : Math.floor(height / 2);
  const shape = await addShape({
    shape_type: "rectangle",
    x: params.x,
    y: params.y,
    width: params.width,
    height,
    hex_color: params.pill_color || "#ff7a00",
    corner_radius: corner,
    opacity: 100,
  });
  const fontSize = params.font_size || Math.max(18, Math.floor(height * 0.38));
  const text = await addTextLayer({
    content: params.text || "Shop Now",
    font_size: fontSize,
    hex_color: params.text_color || "#ffffff",
    x: (params.x || 0) + Math.floor((params.width || 0) / 2),
    y: (params.y || 0) + Math.floor(height * 0.5 + fontSize * 0.32),
    alignment: "center",
    font_name: params.font_name,
  });
  return {
    message: `PILL CTA created at (${params.x},${params.y}).`,
    shape,
    text,
  };
}

async function generateFill(params) {
  const x = params.x || 0;
  const y = params.y || 0;
  const w = params.width || 100;
  const h = params.height || 100;
  await action.batchPlay(
    [
      {
        _obj: "set",
        _target: [{ _ref: "channel", _property: "selection" }],
        to: {
          _obj: "rectangle",
          top: { _unit: "pixelsUnit", _value: y },
          left: { _unit: "pixelsUnit", _value: x },
          bottom: { _unit: "pixelsUnit", _value: y + h },
          right: { _unit: "pixelsUnit", _value: x + w },
        },
      },
      {
        _obj: "generativeFill",
        GFPrompt: params.prompt || "",
        GFSeed: -1,
        GFNumVariations: 1,
      },
    ],
    { synchronousExecution: true }
  );
  return {
    message: `Generative fill applied at (${x},${y}), size ${w}x${h}. Prompt: '${params.prompt || ""}'`,
  };
}

async function executeBatchplay(params) {
  const commands = params.commands || [];
  const result = await action.batchPlay(commands, { synchronousExecution: true });
  return { message: "batchPlay executed.", result };
}

async function executeJsx(params) {
  // UXP does not run ExtendScript directly; expose batchPlay JSON instead.
  throw Object.assign(
    new Error("execute_jsx is only available on the COM/ExtendScript fallback bridge."),
    { code: "UNSUPPORTED_ON_UXP" }
  );
}

const HANDLERS = {
  ping: async () => ({ pong: true, backend: "uxp", plugin_version: PLUGIN_VERSION }),
  get_status: async () => ({
    connected: true,
    backend: "uxp",
    has_document: app.documents.length > 0,
    document_name: app.documents.length ? app.activeDocument.name : null,
    photoshop_version: photoshopVersion(),
    plugin_version: PLUGIN_VERSION,
  }),
  create_document: createDocument,
  open_document: openDocument,
  close_document: closeDocument,
  save_document: saveDocument,
  export_png: exportPng,
  get_layer_context: getLayerContext,
  add_text_layer: addTextLayer,
  set_layer_properties: setLayerProperties,
  move_layer: moveLayer,
  rotate_layer: rotateLayer,
  scale_layer: scaleLayer,
  reorder_layer: reorderLayer,
  add_solid_color_layer: addSolidColorLayer,
  add_gradient_layer: addGradientLayer,
  add_shape: addShape,
  change_shape_color: changeShapeColor,
  add_stroke: addStroke,
  add_image_layer: addImageLayer,
  add_element_layer: addElementLayer,
  add_pill_cta: addPillCta,
  select_subject_and_mask: selectSubjectAndMask,
  generate_fill: generateFill,
  history_checkpoint: historyCheckpoint,
  history_undo: historyUndo,
  execute_batchplay: executeBatchplay,
  execute_jsx: executeJsx,
};

async function handleRequest(msg) {
  const id = msg.id;
  const method = msg.method;
  const params = msg.params || {};
  const checkpoint = !!msg.checkpoint;
  try {
    const handler = HANDLERS[method];
    if (!handler) {
      throw Object.assign(new Error(`Unsupported method: ${method}`), {
        code: "UNSUPPORTED_METHOD",
      });
    }
    const result = await core.executeAsModal(
      () => withCheckpoint(checkpoint, () => handler(params)),
      { commandName: `DES.ai.N:${method}` }
    );
    return {
      id,
      type: "response",
      ok: true,
      result: result || {},
      protocol: PROTOCOL,
    };
  } catch (err) {
    return {
      id,
      type: "response",
      ok: false,
      error: {
        code: err.code || "PHOTOSHOP_ERROR",
        message: String(err.message || err),
        retryable: false,
      },
      protocol: PROTOCOL,
    };
  }
}

function clearReconnect() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
}

function scheduleReconnect() {
  if (intentionalClose) return;
  clearReconnect();
  const delay = Math.min(30000, 1000 * Math.pow(2, reconnectAttempt));
  reconnectAttempt += 1;
  setStatus(`Disconnected. Reconnecting in ${Math.round(delay / 1000)}s…`, "bad");
  reconnectTimer = setTimeout(connect, delay);
}

function connect() {
  clearReconnect();
  intentionalClose = false;
  const url = (urlEl.value || "ws://127.0.0.1:8765").trim();
  setStatus(`Connecting to ${url}…`);
  try {
    socket = new WebSocket(url);
  } catch (e) {
    setStatus(`Failed to open WebSocket: ${e}`, "bad");
    scheduleReconnect();
    return;
  }

  socket.onopen = () => {
    reconnectAttempt = 0;
    setStatus(`Connected to ${url}`, "ok");
    socket.send(
      JSON.stringify({
        type: "hello",
        role: "uxp",
        photoshop_version: photoshopVersion(),
        plugin_version: PLUGIN_VERSION,
        protocol: PROTOCOL,
      })
    );
  };

  socket.onmessage = async (event) => {
    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch (e) {
      return;
    }
    if (msg.type !== "request") return;
    const response = await handleRequest(msg);
    if (socket && socket.readyState === 1) {
      socket.send(JSON.stringify(response));
    }
  };

  socket.onclose = () => {
    socket = null;
    if (!intentionalClose) scheduleReconnect();
    else setStatus("Disconnected", "bad");
  };

  socket.onerror = () => {
    setStatus("WebSocket error", "bad");
  };
}

function disconnect() {
  intentionalClose = true;
  clearReconnect();
  if (socket) {
    try {
      socket.close();
    } catch (e) {}
  }
  socket = null;
  setStatus("Disconnected", "bad");
}

connectBtn.addEventListener("click", connect);
disconnectBtn.addEventListener("click", disconnect);

// Auto-connect on panel load for smoother agent workflows.
connect();
