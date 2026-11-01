/* arena3d.js — tiny hand-rolled WebGL renderer for the dashboard's two hero
   models (football + arena cup). No framework and no CDN: the site's CSP is
   script-src 'self', and two decorative models do not justify weakening it
   or shipping a 700 KB library. Everything is procedural: the ball's panels
   are coloured by distance to the icosahedron's vertex directions, the cup
   is a lathe profile with torus handles. Falls back to the static assets
   already in the markup when WebGL is unavailable. */
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
    "void main() {",
    "  vec4 world = uModel * vec4(aPos, 1.0);",
    "  vWorld = world.xyz;",
    "  vNorm = mat3(uModel) * aNorm;",
    "  vCol = aCol;",
    "  gl_Position = uMVP * vec4(aPos, 1.0);",
    "}"
  ].join("\n");

  var FSH = [
    "precision mediump float;",
    "varying vec3 vNorm;",
    "varying vec3 vCol;",
    "varying vec3 vWorld;",
    "uniform vec3 uCam;",
    "uniform vec3 uLight1;",
    "uniform vec3 uLight2;",
    "uniform float uShine;",
    "uniform float uSpec;",
    "uniform float uMetal;",
    "uniform vec3 uRim;",
    "uniform float uRimAmt;",
    "void main() {",
    "  vec3 n = normalize(vNorm);",
    "  vec3 v = normalize(uCam - vWorld);",
    "  float d1 = max(dot(n, normalize(uLight1)), 0.0);",
    "  float d2 = max(dot(n, normalize(uLight2)), 0.0);",
    "  vec3 base = vCol;",
    "  vec3 col = base * (0.34 + d1 * (uMetal > 0.5 ? 0.55 : 0.95) + d2 * 0.30);",
    "  vec3 h = normalize(normalize(uLight1) + v);",
    "  float s = pow(max(dot(n, h), 0.0), uShine) * uSpec;",
    "  col += (uMetal > 0.5 ? base * 1.4 : vec3(1.0)) * s;",
    "  float fres = pow(1.0 - max(dot(n, v), 0.0), 3.0) * uRimAmt;",
    "  col += uRim * fres;",
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
  function icoDirections() {
    var phi = (1 + Math.sqrt(5)) / 2, dirs = [];
    var raw = [];
    [[0, 1, phi], [0, 1, -phi], [0, -1, phi], [0, -1, -phi],
     [1, phi, 0], [1, -phi, 0], [-1, phi, 0], [-1, -phi, 0],
     [phi, 0, 1], [-phi, 0, 1], [phi, 0, -1], [-phi, 0, -1]].forEach(function (p) { raw.push(p); });
    raw.forEach(function (p) {
      var l = Math.hypot(p[0], p[1], p[2]);
      dirs.push([p[0] / l, p[1] / l, p[2] / l]);
    });
    return dirs;
  }
  function smoothstep(a, b, x) {
    var t = Math.min(1, Math.max(0, (x - a) / (b - a)));
    return t * t * (3 - 2 * t);
  }

  function buildBall() {
    var W = 96, H = 72, dirs = icoDirections();
    var pos = [], norm = [], col = [], idx = [];
    var WHITE = [0.955, 0.965, 0.945], DARK = [0.055, 0.06, 0.075], NEON = [0.64, 1.0, 0.07];
    for (var j = 0; j <= H; j++) {
      var v = j / H, theta = v * Math.PI;
      for (var i = 0; i <= W; i++) {
        var u = i / W, phiA = u * Math.PI * 2;
        var x = Math.sin(theta) * Math.cos(phiA), y = Math.cos(theta), z = Math.sin(theta) * Math.sin(phiA);
        pos.push(x, y, z); norm.push(x, y, z);
        var maxDot = -1;
        for (var d = 0; d < 12; d++) {
          var dot = x * dirs[d][0] + y * dirs[d][1] + z * dirs[d][2];
          if (dot > maxDot) maxDot = dot;
        }
        var t = smoothstep(0.906, 0.938, maxDot);
        var r = WHITE[0] + (DARK[0] - WHITE[0]) * t;
        var g = WHITE[1] + (DARK[1] - WHITE[1]) * t;
        var b = WHITE[2] + (DARK[2] - WHITE[2]) * t;
        var seam = 1 - smoothstep(0.0, 0.012, Math.abs(maxDot - 0.922));
        r += (NEON[0] - r) * seam * 0.5; g += (NEON[1] - g) * seam * 0.5; b += (NEON[2] - b) * seam * 0.5;
        col.push(r, g, b);
      }
    }
    for (var jj = 0; jj < H; jj++) for (var ii = 0; ii < W; ii++) {
      var a = jj * (W + 1) + ii, bq = a + W + 1;
      idx.push(a, bq, a + 1, bq, bq + 1, a + 1);
    }
    return { pos: pos, norm: norm, col: col, idx: idx };
  }

  function lathe(profile, segments) {
    var pos = [], norm = [], col = [], idx = [];
    var GOLD = [0.93, 0.72, 0.28];
    var n = profile.length;
    var pn = [];
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
        col.push(GOLD[0], GOLD[1], GOLD[2]);
      }
    }
    for (var jj = 0; jj < n - 1; jj++) for (var ii = 0; ii < segments; ii++) {
      var a2 = jj * (segments + 1) + ii, b2 = a2 + segments + 1;
      idx.push(a2, a2 + 1, b2, b2, a2 + 1, b2 + 1);
    }
    return { pos: pos, norm: norm, col: col, idx: idx };
  }

  function torus(cx, cy, R, tube, arcFrom, arcTo, flip) {
    var pos = [], norm = [], col = [], idx = [];
    var GOLD = [0.93, 0.72, 0.28];
    var U = 26, V = 12;
    for (var j = 0; j <= V; j++) {
      var vv = (j / V) * Math.PI * 2, cv = Math.cos(vv), sv = Math.sin(vv);
      for (var i = 0; i <= U; i++) {
        var uu = arcFrom + (arcTo - arcFrom) * (i / U), cu = Math.cos(uu), su = Math.sin(uu);
        var px = cx + (R + tube * cv) * cu, py = cy + (R + tube * cv) * su, pz = tube * sv;
        pos.push(px, py, pz);
        norm.push(cv * cu, cv * su, sv);
        col.push(GOLD[0], GOLD[1], GOLD[2]);
      }
    }
    for (var jj = 0; jj < V; jj++) for (var ii = 0; ii < U; ii++) {
      var a = jj * (U + 1) + ii, b = a + U + 1;
      if (flip) idx.push(a, b, a + 1, b, b + 1, a + 1);
      else idx.push(a, a + 1, b, b, a + 1, b + 1);
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

  function buildGem(cx, cy, cz, r, color) {
    var pos = [], norm = [], col = [], idx = [];
    var W = 14, H = 10;
    for (var j = 0; j <= H; j++) {
      var v = j / H, th = v * Math.PI;
      for (var i = 0; i <= W; i++) {
        var u = i / W, ph = u * Math.PI * 2;
        var x = Math.sin(th) * Math.cos(ph), y = Math.cos(th), z = Math.sin(th) * Math.sin(ph);
        pos.push(cx + x * r, cy + y * r, cz + z * r);
        norm.push(x, y, z);
        col.push(color[0], color[1], color[2]);
      }
    }
    for (var jj = 0; jj < H; jj++) for (var ii = 0; ii < W; ii++) {
      var a = jj * (W + 1) + ii, b = a + W + 1;
      idx.push(a, b, a + 1, b, b + 1, a + 1);
    }
    return { pos: pos, norm: norm, col: col, idx: idx };
  }

  function buildTrophy() {
    var profile = [
      [0.0, 0.0], [0.52, 0.0], [0.56, 0.05], [0.56, 0.13], [0.32, 0.19], [0.21, 0.28],
      [0.175, 0.52], [0.175, 0.72], [0.28, 0.92], [0.48, 1.16], [0.64, 1.44],
      [0.72, 1.70], [0.74, 1.88], [0.70, 1.92], [0.665, 1.80]
    ];
    var cup = lathe(profile, 72);
    var right = torus(0.50, 1.40, 0.30, 0.06, -Math.PI * 0.46, Math.PI * 0.46, false);
    var left = torus(-0.50, 1.40, 0.30, 0.06, Math.PI * 0.54, Math.PI * 1.46, true);
    var NEONC = [0.64, 1.0, 0.07];
    var gems = [0, 1, 2].map(function (k) {
      var a = k * Math.PI * 2 / 3 + 0.5;
      return buildGem(Math.cos(a) * 0.705, 1.52, Math.sin(a) * 0.705, 0.05, NEONC);
    });
    return merge([cup, right, left].concat(gems));
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
    gl.useProgram(prog);
    this.prog = prog;
    var geom = kind === "ball" ? buildBall() : buildTrophy();
    function buffer(data, isIndex) {
      var buf = gl.createBuffer();
      gl.bindBuffer(isIndex ? gl.ELEMENT_ARRAY_BUFFER : gl.ARRAY_BUFFER, buf);
      gl.bufferData(isIndex ? gl.ELEMENT_ARRAY_BUFFER : gl.ARRAY_BUFFER,
        isIndex ? new Uint32Array(data) : new Float32Array(data), gl.STATIC_DRAW);
      return buf;
    }
    if (!gl.getExtension("OES_element_index_uint")) { this.gl = null; return; }
    this.count = geom.idx.length;
    this.bPos = buffer(geom.pos); this.bNorm = buffer(geom.norm); this.bCol = buffer(geom.col); this.bIdx = buffer(geom.idx, true);
    this.uMVP = gl.getUniformLocation(prog, "uMVP");
    this.uModel = gl.getUniformLocation(prog, "uModel");
    this.uCam = gl.getUniformLocation(prog, "uCam");
    this.uL1 = gl.getUniformLocation(prog, "uLight1");
    this.uL2 = gl.getUniformLocation(prog, "uLight2");
    this.uShine = gl.getUniformLocation(prog, "uShine");
    this.uSpec = gl.getUniformLocation(prog, "uSpec");
    this.uMetal = gl.getUniformLocation(prog, "uMetal");
    this.uRim = gl.getUniformLocation(prog, "uRim");
    this.uRimAmt = gl.getUniformLocation(prog, "uRimAmt");
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
      this.velY += ((0.28 * auto) - this.velY) * Math.min(1, dt * 1.6);
      if (!this.dragging) this.rotY += this.velY * dt;
      this.rotX += Math.sin(t * 0.0006) * 0.00012 * auto;
    } else {
      this.rotY += 0.32 * dt * auto;
    }
    var bob = this.kind === "ball" ? Math.sin(t * 0.0011) * 0.055 * auto : 0;
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    gl.useProgram(this.prog);
    var proj = perspective(0.56, this.aspect, 0.1, 50);
    var dist = this.kind === "ball" ? 4.0 : 4.35;
    var view = new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, -dist, 1]);
    var yOff = this.kind === "ball" ? bob : -0.94;
    var model = modelMatrix(0, yOff, 0, this.rotX, this.rotY, 1);
    var mvp = multiply(proj, multiply(view, model));
    var worldModel = modelMatrix(0, 0, 0, this.rotX, this.rotY, 1);
    // the visible model sits at (0, yOff, -0) in view space; shading uses the
    // rotation-only model so normals stay consistent while it bobs.
    gl.uniformMatrix4fv(this.uMVP, false, mvp);
    gl.uniformMatrix4fv(this.uModel, false, worldModel);
    gl.uniform3f(this.uCam, 0, 0, dist);
    if (this.kind === "ball") {
      gl.uniform3f(this.uL1, 0.55, 0.85, 0.75);
      gl.uniform3f(this.uL2, -0.65, -0.15, 0.45);
      gl.uniform1f(this.uShine, 55.0);
      gl.uniform1f(this.uSpec, 0.38);
      gl.uniform1f(this.uMetal, 0.0);
      gl.uniform3f(this.uRim, 0.30, 0.65, 0.05);
      gl.uniform1f(this.uRimAmt, 0.35);
    } else {
      var a = t * 0.0009;
      gl.uniform3f(this.uL1, Math.cos(a) * 0.8, 0.75, Math.sin(a) * 0.8 + 0.35);
      gl.uniform3f(this.uL2, -0.5, 0.1, -0.65);
      gl.uniform1f(this.uShine, 85.0);
      gl.uniform1f(this.uSpec, 0.85);
      gl.uniform1f(this.uMetal, 1.0);
      gl.uniform3f(this.uRim, 0.95, 0.75, 0.30);
      gl.uniform1f(this.uRimAmt, 0.5);
    }
    var gl2 = gl;
    [["aPos", this.bPos], ["aNorm", this.bNorm], ["aCol", this.bCol]].forEach(function (pair) {
      var loc = gl2.getAttribLocation(this.prog, pair[0]);
      if (loc < 0) return;
      gl2.bindBuffer(gl2.ARRAY_BUFFER, pair[1]);
      gl2.enableVertexAttribArray(loc);
      gl2.vertexAttribPointer(loc, 3, gl2.FLOAT, false, 0, 0);
    }, this);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.bIdx);
    gl.drawElements(gl.TRIANGLES, this.count, gl.UNSIGNED_INT, 0);
    if (this.shadowEl) {
      var s = this.kind === "ball" ? 1 - (bob + 0.055) * 0.55 : 1;
      this.shadowEl.style.transform = "translateX(-50%) scaleX(" + s.toFixed(3) + ")";
      this.shadowEl.style.opacity = this.kind === "ball" ? (0.5 - (bob + 0.055) * 1.1).toFixed(3) : "0.5";
    }
  };

  /* ——— boot ——— */
  var stages = [];
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
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
