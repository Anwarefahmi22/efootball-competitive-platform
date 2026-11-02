/* arena3d.js v2 — hand-rolled WebGL renderer for the dashboard's football
   and arena cup, shaded to a photographic standard (user's bar: the landing
   page's real ball and a real 🏆). No framework, no CDN (CSP is script-src
   'self'). What makes it read as real instead of a flat render:
   - Ball: panels computed per-fragment from the icosahedron directions
     (crisp at any zoom), procedural leather grain, dark stitched grooves
     with ambient occlusion rolling into the seams, a studio-environment
     reflection swept by a fresnel term, tight clearcoat-style specular.
   - Cup: gold is mostly reflected environment, so the shader reflects a
     procedural studio (ceiling softbox + side strips + pitch bounce) tinted
     by the metal, over a lathe body with lip/stem rings and handles, plus
     fine vertical brushing noise.
   The photo assets stay in the markup as the no-WebGL fallback. */
(function () {
  "use strict";

  var VSH = [
    "attribute vec3 aPos;",
    "attribute vec3 aNorm;",
    "attribute vec3 aCol;",
    "uniform mat4 uMVP;",
    "uniform mat4 uModel;",
    "varying vec3 vNorm;",
    "varying vec3 vCol;",
    "varying vec3 vWorld;",
    "varying vec3 vObj;",
    "void main() {",
    "  vec4 world = uModel * vec4(aPos, 1.0);",
    "  vWorld = world.xyz;",
    "  vNorm = mat3(uModel) * aNorm;",
    "  vCol = aCol;",
    "  vObj = aPos;",
    "  gl_Position = uMVP * vec4(aPos, 1.0);",
    "}"
  ].join("\n");

  var FSH = [
    "precision mediump float;",
    "varying vec3 vNorm;",
    "varying vec3 vCol;",
    "varying vec3 vWorld;",
    "varying vec3 vObj;",
    "uniform vec3 uCam;",
    "uniform vec3 uLight1;",
    "uniform vec3 uLight2;",
    "uniform float uKind;",
    "float hash(vec3 p) { return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453123); }",
    "float vnoise(vec3 p) {",
    "  vec3 i = floor(p); vec3 f = fract(p); f = f * f * (3.0 - 2.0 * f);",
    "  float n000 = hash(i); float n100 = hash(i + vec3(1.0, 0.0, 0.0));",
    "  float n010 = hash(i + vec3(0.0, 1.0, 0.0)); float n110 = hash(i + vec3(1.0, 1.0, 0.0));",
    "  float n001 = hash(i + vec3(0.0, 0.0, 1.0)); float n101 = hash(i + vec3(1.0, 0.0, 1.0));",
    "  float n011 = hash(i + vec3(0.0, 1.0, 1.0)); float n111 = hash(i + vec3(1.0, 1.0, 1.0));",
    "  return mix(mix(mix(n000, n100, f.x), mix(n010, n110, f.x), f.y),",
    "             mix(mix(n001, n101, f.x), mix(n011, n111, f.x), f.y), f.z);",
    "}",
    "vec3 studioEnv(vec3 r) {",
    "  float h = clamp(r.y * 0.5 + 0.5, 0.0, 1.0);",
    "  vec3 c = mix(vec3(0.012, 0.028, 0.018), vec3(0.10, 0.17, 0.12), pow(h, 1.4));",
    "  c += vec3(1.05, 1.0, 0.88) * pow(max(dot(r, normalize(vec3(0.25, 0.9, 0.35))), 0.0), 16.0) * 1.35;",
    "  c += vec3(0.85, 0.93, 1.0) * pow(max(dot(r, normalize(vec3(-0.85, 0.18, 0.42))), 0.0), 26.0) * 0.75;",
    "  c += vec3(1.0, 0.88, 0.66) * pow(max(dot(r, normalize(vec3(0.82, -0.02, -0.45))), 0.0), 22.0) * 0.65;",
    "  c += vec3(0.55, 0.75, 0.35) * pow(max(dot(r, normalize(vec3(-0.2, -0.85, -0.4))), 0.0), 8.0) * 0.25;",
    "  return c;",
    "}",
    "float ballField(vec3 p) {",
    "  float md = 0.0;",
    "  md = max(md, dot(p, vec3(0.0, 0.5257, 0.8507)));",
    "  md = max(md, dot(p, vec3(0.0, 0.5257, -0.8507)));",
    "  md = max(md, dot(p, vec3(0.0, -0.5257, 0.8507)));",
    "  md = max(md, dot(p, vec3(0.0, -0.5257, -0.8507)));",
    "  md = max(md, dot(p, vec3(0.5257, 0.8507, 0.0)));",
    "  md = max(md, dot(p, vec3(0.5257, -0.8507, 0.0)));",
    "  md = max(md, dot(p, vec3(-0.5257, 0.8507, 0.0)));",
    "  md = max(md, dot(p, vec3(-0.5257, -0.8507, 0.0)));",
    "  md = max(md, dot(p, vec3(0.8507, 0.0, 0.5257)));",
    "  md = max(md, dot(p, vec3(0.8507, 0.0, -0.5257)));",
    "  md = max(md, dot(p, vec3(-0.8507, 0.0, 0.5257)));",
    "  md = max(md, dot(p, vec3(-0.8507, 0.0, -0.5257)));",
    "  return md;",
    "}",
    "void main() {",
    "  vec3 n = normalize(vNorm);",
    "  vec3 v = normalize(uCam - vWorld);",
    "  vec3 l1 = normalize(uLight1);",
    "  vec3 l2 = normalize(uLight2);",
    "  float d1 = max(dot(n, l1), 0.0);",
    "  float d2 = max(dot(n, l2), 0.0);",
    "  vec3 r = reflect(-v, n);",
    "  vec3 env = studioEnv(r);",
    "  float fres = pow(1.0 - max(dot(n, v), 0.0), 3.0);",
    "  vec3 col;",
    "  if (uKind < 0.5) {",
    "    vec3 p = normalize(vObj);",
    "    float md = ballField(p);",
    "    float panel = smoothstep(0.906, 0.938, md);",
    "    vec3 albedo = mix(vec3(0.96, 0.965, 0.95), vec3(0.045, 0.05, 0.065), panel);",
    "    float grain = vnoise(p * 80.0) * 0.6 + vnoise(p * 190.0) * 0.4;",
    "    albedo *= 0.93 + 0.11 * grain;",
    "    float groove = 1.0 - smoothstep(0.0, 0.013, abs(md - 0.922));",
    "    albedo = mix(albedo, vec3(0.02, 0.02, 0.025), groove * 0.8);",
    "    float aoBand = 1.0 - smoothstep(0.0, 0.055, abs(md - 0.922));",
    "    vec3 base = albedo * (0.30 + d1 * 0.95 + d2 * 0.30) * (1.0 - aoBand * 0.16);",
    "    vec3 hv = normalize(l1 + v);",
    "    base += vec3(1.0) * pow(max(dot(n, hv), 0.0), 60.0) * 0.5 * (1.0 - groove * 0.7);",
    "    base += env * (0.05 + 0.38 * fres) * mix(1.0, 0.55, panel) * (1.0 - groove * 0.6);",
    "    col = base;",
    "  } else {",
    "    float brush = vnoise(vec3(vObj.x * 140.0, vObj.y * 10.0, vObj.z * 140.0));",
    "    vec3 envM = env * (0.90 + 0.16 * brush);",
    "    col = vCol * envM * 1.25;",
    "    col += vCol * (d1 * 0.30 + d2 * 0.10);",
    "    vec3 hv = normalize(l1 + v);",
    "    col += vCol * pow(max(dot(n, hv), 0.0), 90.0) * 0.9;",
    "    col += vec3(1.0, 0.85, 0.55) * pow(max(dot(r, l1), 0.0), 42.0) * 0.35;",
    "    col *= 0.92 + 0.16 * fres;",
    "  }",
    "  gl_FragColor = vec4(col, 1.0);",
    "}"
  ].join("\n");

  /* ——— minimal mat4 (column-major) ——— */
  function perspective(fovY, aspect, near, far) {
    var f = 1 / Math.tan(fovY / 2), nf = 1 / (near - far);
    return new Float32Array([f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) * nf, -1, 0, 0, 2 * far * near * nf, 0]);
  }
  function multiply(a, b) {
    var out = new Float32Array(16);
    for (var c = 0; c < 4; c++) for (var r = 0; r < 4; r++) {
      var s = 0;
      for (var k = 0; k < 4; k++) s += a[k * 4 + r] * b[c * 4 + k];
      out[c * 4 + r] = s;
    }
    return out;
  }
  function modelMatrix(tx, ty, tz, rx, ry, scale) {
    var cx = Math.cos(rx), sx = Math.sin(rx), cy = Math.cos(ry), sy = Math.sin(ry);
    var rot = new Float32Array([
      cy, 0, -sy, 0,
      sx * sy, cx, sx * cy, 0,
      cx * sy, -sx, cx * cy, 0,
      0, 0, 0, 1
    ]);
    rot[0] *= scale; rot[1] *= scale; rot[2] *= scale;
    rot[4] *= scale; rot[5] *= scale; rot[6] *= scale;
    rot[8] *= scale; rot[9] *= scale; rot[10] *= scale;
    rot[12] = tx; rot[13] = ty; rot[14] = tz;
    return rot;
  }

  /* ——— geometry ——— */
  function buildBall() {
    var W = 110, H = 84;
    var pos = [], norm = [], col = [], idx = [];
    for (var j = 0; j <= H; j++) {
      var v = j / H, theta = v * Math.PI;
      for (var i = 0; i <= W; i++) {
        var u = i / W, phiA = u * Math.PI * 2;
        var x = Math.sin(theta) * Math.cos(phiA), y = Math.cos(theta), z = Math.sin(theta) * Math.sin(phiA);
        pos.push(x, y, z); norm.push(x, y, z); col.push(1, 1, 1);
      }
    }
    for (var jj = 0; jj < H; jj++) for (var ii = 0; ii < W; ii++) {
      var a = jj * (W + 1) + ii, bq = a + W + 1;
      idx.push(a, bq, a + 1, bq, bq + 1, a + 1);
    }
    return { pos: pos, norm: norm, col: col, idx: idx };
  }

  function lathe(profile, segments, color) {
    var pos = [], norm = [], col = [], idx = [];
    var n = profile.length, pn = [];
    for (var k = 0; k < n; k++) {
      var p0 = profile[Math.max(0, k - 1)], p1 = profile[Math.min(n - 1, k + 1)];
      var dr = p1[0] - p0[0], dy = p1[1] - p0[1];
      var nx = dy, ny = -dr, l = Math.hypot(nx, ny) || 1;
      pn.push([nx / l, ny / l]);
    }
    for (var j = 0; j < n; j++) {
      for (var i = 0; i <= segments; i++) {
        var a = (i / segments) * Math.PI * 2, ca = Math.cos(a), sa = Math.sin(a);
        pos.push(profile[j][0] * ca, profile[j][1], profile[j][0] * sa);
        norm.push(pn[j][0] * ca, pn[j][1], pn[j][0] * sa);
        col.push(color[0], color[1], color[2]);
      }
    }
    for (var jj = 0; jj < n - 1; jj++) for (var ii = 0; ii < segments; ii++) {
      var a2 = jj * (segments + 1) + ii, b2 = a2 + segments + 1;
      idx.push(a2, a2 + 1, b2, b2, a2 + 1, b2 + 1);
    }
    return { pos: pos, norm: norm, col: col, idx: idx };
  }

  function torus(cx, cy, R, tube, arcFrom, arcTo, flip, color) {
    var pos = [], norm = [], col = [], idx = [];
    var U = 26, V = 12;
    for (var j = 0; j <= V; j++) {
      var vv = (j / V) * Math.PI * 2, cv = Math.cos(vv), sv = Math.sin(vv);
      for (var i = 0; i <= U; i++) {
        var uu = arcFrom + (arcTo - arcFrom) * (i / U), cu = Math.cos(uu), su = Math.sin(uu);
        pos.push(cx + (R + tube * cv) * cu, cy + (R + tube * cv) * su, tube * sv);
        norm.push(cv * cu, cv * su, sv);
        col.push(color[0], color[1], color[2]);
      }
    }
    for (var jj = 0; jj < V; jj++) for (var ii = 0; ii < U; ii++) {
      var a = jj * (U + 1) + ii, b = a + U + 1;
      if (flip) idx.push(a, b, a + 1, b, b + 1, a + 1);
      else idx.push(a, a + 1, b, b, a + 1, b + 1);
    }
    return { pos: pos, norm: norm, col: col, idx: idx };
  }

  /* ring lying around the Y axis (lip and stem detailing) */
  function ringY(cy, R, tube, color) {
    var pos = [], norm = [], col = [], idx = [];
    var U = 64, V = 12;
    for (var j = 0; j <= V; j++) {
      var vv = (j / V) * Math.PI * 2, cv = Math.cos(vv), sv = Math.sin(vv);
      for (var i = 0; i <= U; i++) {
        var uu = (i / U) * Math.PI * 2, cu = Math.cos(uu), su = Math.sin(uu);
        pos.push((R + tube * cv) * cu, cy + tube * sv, (R + tube * cv) * su);
        norm.push(cv * cu, sv, cv * su);
        col.push(color[0], color[1], color[2]);
      }
    }
    for (var jj = 0; jj < V; jj++) for (var ii = 0; ii < U; ii++) {
      var a = jj * (U + 1) + ii, b = a + U + 1;
      idx.push(a, a + 1, b, b, a + 1, b + 1);
    }
    return { pos: pos, norm: norm, col: col, idx: idx };
  }

  function merge(geoms) {
    var pos = [], norm = [], col = [], idx = [], off = 0;
    geoms.forEach(function (g) {
      pos = pos.concat(g.pos); norm = norm.concat(g.norm); col = col.concat(g.col);
      g.idx.forEach(function (i) { idx.push(i + off); });
      off += g.pos.length / 3;
    });
    return { pos: pos, norm: norm, col: col, idx: idx };
  }

  var GOLD = [0.93, 0.72, 0.28];
  function buildTrophy() {
    var profile = [
      [0.0, 0.0], [0.52, 0.0], [0.56, 0.05], [0.56, 0.13], [0.32, 0.19], [0.21, 0.28],
      [0.175, 0.52], [0.175, 0.72], [0.28, 0.92], [0.48, 1.16], [0.64, 1.44],
      [0.72, 1.70], [0.74, 1.88], [0.70, 1.92], [0.665, 1.80]
    ];
    return merge([
      lathe(profile, 80, GOLD),
      torus(0.50, 1.40, 0.30, 0.06, -Math.PI * 0.46, Math.PI * 0.46, false, GOLD),
      torus(-0.50, 1.40, 0.30, 0.06, Math.PI * 0.54, Math.PI * 1.46, true, GOLD),
      ringY(1.90, 0.715, 0.030, GOLD),
      ringY(0.62, 0.178, 0.020, GOLD)
    ]);
  }

  /* ——— stage ——— */
  function Stage(canvas, kind) {
    this.canvas = canvas;
    this.kind = kind;
    this.gl = canvas.getContext("webgl", { antialias: true, alpha: true });
    if (!this.gl) return;
    var gl = this.gl;
    function shader(type, src) {
      var sh = gl.createShader(type);
      gl.shaderSource(sh, src); gl.compileShader(sh);
      return sh;
    }
    var prog = gl.createProgram();
    gl.attachShader(prog, shader(gl.VERTEX_SHADER, VSH));
    gl.attachShader(prog, shader(gl.FRAGMENT_SHADER, FSH));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) { this.gl = null; return; }
    if (!gl.getExtension("OES_element_index_uint")) { this.gl = null; return; }
    gl.useProgram(prog);
    this.prog = prog;
    this.u = {};
    ["uMVP", "uModel", "uCam", "uLight1", "uLight2", "uKind"].forEach(function (name) {
      this.u[name] = gl.getUniformLocation(prog, name);
    }, this);
    this.aPos = gl.getAttribLocation(prog, "aPos");
    this.aNorm = gl.getAttribLocation(prog, "aNorm");
    this.aCol = gl.getAttribLocation(prog, "aCol");
    function buffer(data, isIndex) {
      var buf = gl.createBuffer();
      gl.bindBuffer(isIndex ? gl.ELEMENT_ARRAY_BUFFER : gl.ARRAY_BUFFER, buf);
      gl.bufferData(isIndex ? gl.ELEMENT_ARRAY_BUFFER : gl.ARRAY_BUFFER,
        isIndex ? new Uint32Array(data) : new Float32Array(data), gl.STATIC_DRAW);
      return buf;
    }
    var geom = kind === "ball" ? buildBall() : buildTrophy();
    this.count = geom.idx.length;
    this.bPos = buffer(geom.pos); this.bNorm = buffer(geom.norm);
    this.bCol = buffer(geom.col); this.bIdx = buffer(geom.idx, true);
    this.reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    this.rotX = kind === "ball" ? 0.42 : -0.06;
    this.rotY = kind === "ball" ? -0.6 : 0.5;
    this.velY = 0;
    this.visible = false;
    this.resize();
  }
  Stage.prototype.resize = function () {
    var dpr = Math.min(window.devicePixelRatio || 1, 1.75);
    var w = this.canvas.clientWidth || 180, h = this.canvas.clientHeight || 180;
    this.canvas.width = Math.round(w * dpr);
    this.canvas.height = Math.round(h * dpr);
    this.aspect = w / h;
  };
  Stage.prototype.draw = function (t, dt) {
    var gl = this.gl;
    if (!gl) return;
    var auto = this.reduced ? 0 : 1;
    if (this.kind === "ball") {
      this.velY += (0.4 * auto - this.velY) * Math.min(1, dt * 1.6);
      if (!this.dragging) this.rotY += this.velY * dt;
      this.rotX += Math.sin(t * 0.0006) * 0.00012 * auto;
    } else {
      this.rotY += 0.5 * dt * auto;
    }
    var bob = this.kind === "ball" ? Math.sin(t * 0.0011) * 0.055 * auto : 0;
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    gl.useProgram(this.prog);
    var dist = this.kind === "ball" ? 4.0 : 4.35;
    var proj = perspective(0.56, this.aspect, 0.1, 50);
    var view = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, -dist, 1]);
    var yOff = this.kind === "ball" ? bob : -0.94;
    var model = modelMatrix(0, yOff, 0, this.rotX, this.rotY, 1);
    var mvp = multiply(proj, multiply(view, model));
    var worldModel = modelMatrix(0, 0, 0, this.rotX, this.rotY, 1);
    gl.uniformMatrix4fv(this.u.uMVP, false, mvp);
    gl.uniformMatrix4fv(this.u.uModel, false, worldModel);
    gl.uniform3f(this.u.uCam, 0, 0, dist);
    gl.uniform3f(this.u.uLight1, 0.55, 0.85, 0.75);
    gl.uniform3f(this.u.uLight2, -0.65, -0.15, 0.45);
    gl.uniform1f(this.u.uKind, this.kind === "ball" ? 0.0 : 1.0);
    var binds = [[this.aPos, this.bPos], [this.aNorm, this.bNorm], [this.aCol, this.bCol]];
    for (var bi = 0; bi < binds.length; bi++) {
      if (binds[bi][0] < 0) continue;
      gl.bindBuffer(gl.ARRAY_BUFFER, binds[bi][1]);
      gl.enableVertexAttribArray(binds[bi][0]);
      gl.vertexAttribPointer(binds[bi][0], 3, gl.FLOAT, false, 0, 0);
    }
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.bIdx);
    gl.drawElements(gl.TRIANGLES, this.count, gl.UNSIGNED_INT, 0);
    if (this.shadowEl) {
      var s = this.kind === "ball" ? 1 - (bob + 0.055) * 0.55 : 1;
      this.shadowEl.style.transform = "translateX(-50%) scaleX(" + s.toFixed(3) + ")";
      this.shadowEl.style.opacity = this.kind === "ball" ? (0.62 - (bob + 0.055) * 1.4).toFixed(3) : "0.62";
    }
  };

  /* ——— boot ——— */
  var stages = [];
  function init() {
    document.querySelectorAll("canvas[data-arena3d]").forEach(function (canvas) {
      var stage = null;
      try { stage = new Stage(canvas, canvas.getAttribute("data-arena3d")); } catch (e) { stage = null; }
      var wrap = canvas.closest(".stage3d");
      var fallback = wrap ? wrap.querySelector(".stage3d__fallback") : null;
      if (!stage || !stage.gl) {
        canvas.remove();
        if (fallback) fallback.hidden = false;
        return;
      }
      if (fallback) fallback.remove();
      canvas.hidden = false;
      stage.shadowEl = wrap ? wrap.querySelector(".stage3d__shadow") : null;
      stages.push(stage);
      if ("IntersectionObserver" in window) {
        new IntersectionObserver(function (entries) {
          entries.forEach(function (en) { stage.visible = en.isIntersecting; });
        }, { threshold: 0.05 }).observe(canvas);
      } else stage.visible = true;
      if (stage.kind === "ball") {
        var lastX = 0, lastY = 0;
        canvas.addEventListener("pointerdown", function (ev) {
          stage.dragging = true; lastX = ev.clientX; lastY = ev.clientY;
          canvas.setPointerCapture(ev.pointerId);
        });
        canvas.addEventListener("pointermove", function (ev) {
          if (!stage.dragging) return;
          var dx = ev.clientX - lastX, dy = ev.clientY - lastY;
          lastX = ev.clientX; lastY = ev.clientY;
          stage.rotY += dx * 0.012;
          stage.rotX = Math.max(-1.1, Math.min(1.1, stage.rotX + dy * 0.008));
          stage.velY = dx * 0.55;
        });
        ["pointerup", "pointercancel"].forEach(function (name) {
          canvas.addEventListener(name, function () { stage.dragging = false; });
        });
      }
    });
    if (!stages.length) return;
    stages.forEach(function (s) { s.draw(600, 0); });
    var last = performance.now();
    function frame(now) {
      var dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      if (!document.hidden) stages.forEach(function (s) { if (s.visible) s.draw(now, dt); });
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
    var resizeTimer = null;
    window.addEventListener("resize", function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () { stages.forEach(function (s) { s.resize(); s.draw(600, 0); }); }, 180);
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
