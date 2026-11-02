/* arena3d.js v8 — hand-rolled WebGL renderer for the dashboard's football
   and arena cup, shaded to a photographic standard (user's bar: the landing
   page's real ball and a real 🏆). No framework, no CDN (CSP script-src
   'self'). Round-3 lessons baked in:
   - A ball reads as a render when its surface is smooth: v3 gives it a
     true cellular pebble-grain height field (3D Voronoi) used as a bump
     map, and folds the panel seams into the same height field so the
     grooves are recessed geometry in the lighting, not painted lines.
   - A surface of revolution CANNOT show Y-rotation under a fixed world
     (its image is mathematically invariant) — so the cup also rocks
     gently, its key light orbits, and it carries an asymmetric front
     medallion; the studio environment it reflects got hotter, narrower
     softboxes so the metal shows defined bands instead of a flat wash.
   Photos stay in the markup as the no-WebGL fallback. */
(function () {
  "use strict";

  var VSH = [
    "attribute vec3 aPos;",
    "attribute vec3 aNorm;",
    "attribute vec3 aCol;",
    "uniform mat4 uMVP;",
    "uniform mat4 uModel;",
    "uniform mat4 uModelFull;",
    "varying vec3 vNorm;",
    "varying vec3 vCol;",
    "varying vec3 vWorld;",
    "varying vec3 vObj;",
    "varying float vDispY;",
    "void main() {",
    "  vec4 world = uModel * vec4(aPos, 1.0);",
    "  vWorld = world.xyz;",
    "  vNorm = mat3(uModel) * aNorm;",
    "  vCol = aCol;",
    "  vObj = aPos;",
    "  vDispY = (uModelFull * vec4(aPos, 1.0)).y;",
    "  gl_Position = uMVP * vec4(aPos, 1.0);",
    "}"
  ].join("\n");

  var FSH = [
    "#ifdef GL_FRAGMENT_PRECISION_HIGH",
    "precision highp float;",
    "#else",
    "precision mediump float;",
    "#endif",
    "varying vec3 vNorm;",
    "varying vec3 vCol;",
    "varying vec3 vWorld;",
    "varying vec3 vObj;",
    "varying float vDispY;",
    "uniform vec3 uCam;",
    "uniform vec3 uLight1;",
    "uniform vec3 uLight2;",
    "uniform float uKind;",
    "uniform float uReflect;",
    "uniform float uBaseY;",
    "vec3 hash3(vec3 p3) {",
    "  p3 = fract(p3 * vec3(0.1031, 0.1030, 0.0973));",
    "  p3 += dot(p3, p3.yxz + 33.33);",
    "  return fract((p3.xxy + p3.yxx) * p3.zyx);",
    "}",
    "float vnoise(vec3 p) {",
    "  vec3 i = floor(p); vec3 f = fract(p); f = f * f * (3.0 - 2.0 * f);",
    "  float n000 = hash3(i).x; float n100 = hash3(i + vec3(1.0, 0.0, 0.0)).x;",
    "  float n010 = hash3(i + vec3(0.0, 1.0, 0.0)).x; float n110 = hash3(i + vec3(1.0, 1.0, 0.0)).x;",
    "  float n001 = hash3(i + vec3(0.0, 0.0, 1.0)).x; float n101 = hash3(i + vec3(1.0, 0.0, 1.0)).x;",
    "  float n011 = hash3(i + vec3(0.0, 1.0, 1.0)).x; float n111 = hash3(i + vec3(1.0, 1.0, 1.0)).x;",
    "  return mix(mix(mix(n000, n100, f.x), mix(n010, n110, f.x), f.y),",
    "             mix(mix(n001, n101, f.x), mix(n011, n111, f.x), f.y), f.z);",
    "}",
    "vec2 voro(vec3 p) {",
    "  vec3 ip = floor(p); vec3 fp = fract(p);",
    "  float f1 = 8.0; float f2 = 8.0;",
    "  for (int k = -1; k <= 1; k++)",
    "  for (int j = -1; j <= 1; j++)",
    "  for (int i = -1; i <= 1; i++) {",
    "    vec3 g = vec3(float(i), float(j), float(k));",
    "    vec3 r = g + hash3(ip + g) - fp;",
    "    float d = dot(r, r);",
    "    if (d < f1) { f2 = f1; f1 = d; } else if (d < f2) { f2 = d; }",
    "  }",
    "  return vec2(sqrt(f1), sqrt(f2));",
    "}",
    "vec3 studioEnv(vec3 r) {",
    "  vec3 c = vec3(0.008, 0.016, 0.010);",
    "  c += vec3(1.10, 1.02, 0.86) * pow(max(dot(r, normalize(vec3(0.25, 0.90, 0.35))), 0.0), 90.0) * 2.2;",
    "  c += vec3(0.82, 0.92, 1.00) * pow(max(dot(r, normalize(vec3(-0.90, 0.05, 0.44))), 0.0), 140.0) * 1.4;",
    "  c += vec3(1.00, 0.90, 0.70) * pow(max(dot(r, normalize(vec3(0.0, 0.35, 0.94))), 0.0), 70.0) * 0.9;",
    "  c += vec3(0.50, 0.70, 0.32) * pow(max(dot(r, normalize(vec3(-0.2, -0.85, -0.4))), 0.0), 8.0) * 0.22;",
    "  return c;",
    "}",
    "vec3 ballField(vec3 p) {",
    "  float d1 = 0.0; float d2 = 0.0; float dP = 0.0;",
    "  { float dd = dot(p, vec3(0.0000, 0.5257, 0.8507)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } if (dd > dP) dP = dd; }",
    "  { float dd = dot(p, vec3(0.5257, 0.8507, 0.0000)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } if (dd > dP) dP = dd; }",
    "  { float dd = dot(p, vec3(0.8507, 0.0000, 0.5257)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } if (dd > dP) dP = dd; }",
    "  { float dd = dot(p, vec3(0.0000, 0.5257, -0.8507)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } if (dd > dP) dP = dd; }",
    "  { float dd = dot(p, vec3(0.5257, -0.8507, 0.0000)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } if (dd > dP) dP = dd; }",
    "  { float dd = dot(p, vec3(0.8507, 0.0000, -0.5257)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } if (dd > dP) dP = dd; }",
    "  { float dd = dot(p, vec3(0.0000, -0.5257, 0.8507)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } if (dd > dP) dP = dd; }",
    "  { float dd = dot(p, vec3(-0.5257, 0.8507, 0.0000)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } if (dd > dP) dP = dd; }",
    "  { float dd = dot(p, vec3(-0.8507, 0.0000, 0.5257)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } if (dd > dP) dP = dd; }",
    "  { float dd = dot(p, vec3(0.0000, -0.5257, -0.8507)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } if (dd > dP) dP = dd; }",
    "  { float dd = dot(p, vec3(-0.5257, -0.8507, 0.0000)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } if (dd > dP) dP = dd; }",
    "  { float dd = dot(p, vec3(-0.8507, 0.0000, -0.5257)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } if (dd > dP) dP = dd; }",
    "  { float dd = dot(p, vec3(0.5774, 0.5774, 0.5774)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } }",
    "  { float dd = dot(p, vec3(0.0000, 0.9342, 0.3568)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } }",
    "  { float dd = dot(p, vec3(0.3568, 0.0000, 0.9342)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } }",
    "  { float dd = dot(p, vec3(-0.3568, 0.0000, 0.9342)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } }",
    "  { float dd = dot(p, vec3(-0.5774, 0.5774, 0.5774)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } }",
    "  { float dd = dot(p, vec3(0.9342, 0.3568, 0.0000)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } }",
    "  { float dd = dot(p, vec3(0.5774, 0.5774, -0.5774)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } }",
    "  { float dd = dot(p, vec3(0.0000, 0.9342, -0.3568)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } }",
    "  { float dd = dot(p, vec3(0.9342, -0.3568, 0.0000)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } }",
    "  { float dd = dot(p, vec3(0.5774, -0.5774, 0.5774)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } }",
    "  { float dd = dot(p, vec3(0.3568, 0.0000, -0.9342)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } }",
    "  { float dd = dot(p, vec3(-0.5774, 0.5774, -0.5774)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } }",
    "  { float dd = dot(p, vec3(-0.3568, 0.0000, -0.9342)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } }",
    "  { float dd = dot(p, vec3(0.5774, -0.5774, -0.5774)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } }",
    "  { float dd = dot(p, vec3(0.0000, -0.9342, 0.3568)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } }",
    "  { float dd = dot(p, vec3(0.0000, -0.9342, -0.3568)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } }",
    "  { float dd = dot(p, vec3(-0.5774, -0.5774, 0.5774)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } }",
    "  { float dd = dot(p, vec3(-0.9342, 0.3568, 0.0000)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } }",
    "  { float dd = dot(p, vec3(-0.9342, -0.3568, 0.0000)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } }",
    "  { float dd = dot(p, vec3(-0.5774, -0.5774, -0.5774)); if (dd > d1) { d2 = d1; d1 = dd; } else if (dd > d2) { d2 = dd; } }",
    "  return vec3(d1, d2, dP);",
    "}",
    "float ballHeight(vec3 p) {",
    "  vec2 fA = voro(p * 17.0);",
    "  float peb = smoothstep(0.05, 0.6, clamp((fA.y - fA.x) * 2.4, 0.0, 1.0)) * 0.05;",
    "  vec3 bf = ballField(p);",
    "  float sd = bf.x - bf.y;",
    "  float gw = max(0.0, 1.0 - sd / 0.016);",
    "  float puff = clamp(sd / 0.045, 0.0, 1.0);",
    "  return peb + puff * 0.5 - gw * gw * 1.6;",
    "}",
    "void main() {",
    "  vec3 n = normalize(vNorm);",
    "  vec3 v = normalize(uCam - vWorld);",
    "  vec3 l1 = normalize(uLight1);",
    "  vec3 l2 = normalize(uLight2);",
    "  float fres = pow(1.0 - max(dot(n, v), 0.0), 3.0);",
    "  vec3 col;",
    "  if (uKind < 0.5) {",
    "    vec3 p = normalize(vObj);",
    "    vec3 t1 = normalize(cross(vec3(0.0, 1.0, 0.0), p) + vec3(0.001, 0.0, 0.0));",
    "    vec3 t2 = normalize(cross(p, t1));",
    "    float e = 0.012;",
    "    float h0 = ballHeight(p);",
    "    float hx = ballHeight(normalize(p + t1 * e));",
    "    float hy = ballHeight(normalize(p + t2 * e));",
    "    vec3 bn = normalize(n - (t1 * (hx - h0) + t2 * (hy - h0)) * 1.4);",
    "    vec3 bf = ballField(p);",
    "    float sd = bf.x - bf.y;",
    "    float panel = smoothstep(0.906, 0.938, bf.z);",
    "    vec3 albedo = mix(vec3(0.96, 0.965, 0.95), vec3(0.045, 0.05, 0.065), panel);",
    "    albedo *= 0.988 + 0.024 * vnoise(p * 60.0);",
    "    float gJit = vnoise(p * 120.0);",
    "    float groove = 1.0 - smoothstep(0.0, 0.016, sd);",
    "    albedo = mix(albedo, vec3(0.015, 0.015, 0.02), groove * 0.92);",
    "    float stitch = groove * step(0.72, vnoise(p * 300.0));",
    "    albedo = mix(albedo, vec3(0.72, 0.70, 0.62), stitch * 0.45);",
    "    float aoBand = 1.0 - smoothstep(0.0, 0.07, sd);",
    "    float d1w = pow(clamp((dot(bn, l1) + 0.35) / 1.35, 0.0, 1.0), 1.3);",
    "    float d2 = max(dot(bn, l2), 0.0);",
    "    vec3 base = albedo * (0.30 + d1w * 0.95 + d2 * 0.30) * (1.0 - aoBand * 0.22);",
    "    vec3 r = reflect(-v, bn);",
    "    vec3 env = studioEnv(r);",
    "    vec3 hv = normalize(l1 + v);",
    "    base += vec3(1.0) * pow(max(dot(bn, hv), 0.0), 70.0) * 0.75 * (0.8 + 0.45 * gJit) * (1.0 - groove * 0.7) * mix(1.0, 0.75, panel);",
    "    base += env * (0.13 + 0.45 * fres) * (0.92 + 0.14 * gJit) * mix(1.0, 0.55, panel) * (1.0 - groove * 0.6);",
    "    col = base;",
    "  } else if (uKind < 1.5) {",
    "    float d1 = max(dot(n, l1), 0.0);",
    "    float d2 = max(dot(n, l2), 0.0);",
    "    vec3 r = reflect(-v, n);",
    "    vec3 env = studioEnv(r);",
    "    float brush = vnoise(vec3(vObj.x * 140.0, vObj.y * 10.0, vObj.z * 140.0));",
    "    vec3 envM = env * (0.90 + 0.16 * brush);",
    "    col = vCol * envM * 1.5;",
    "    col += vCol * (d1 * 0.18 + d2 * 0.10);",
    "    vec3 hv = normalize(l1 + v);",
    "    col += vCol * pow(max(dot(n, hv), 0.0), 90.0) * 1.1;",
    "    col += vec3(1.0, 0.85, 0.55) * pow(max(dot(r, l1), 0.0), 42.0) * 0.4;",
    "    col *= 0.92 + 0.16 * fres;",
    "  } else {",
    "    float rr = length(vec2(vObj.x, vObj.y - 1.30)) / 0.26;",
    "    float d1 = max(dot(n, l1), 0.0);",
    "    vec3 pc = vCol * (studioEnv(reflect(-v, n)) * 1.2 + d1 * 0.35);",
    "    vec3 hv2 = normalize(l1 + v);",
    "    pc += vec3(1.0) * pow(max(dot(n, hv2), 0.0), 60.0) * 0.5;",
    "    pc *= 1.0 - smoothstep(0.80, 0.99, rr) * 0.55;",
    "    col = pc;",
    "  }",
    "  col = pow(col / (col + 0.82) * 1.30, vec3(0.92));",
    "  float alpha = 1.0;",
    "  if (uReflect > 0.5) { alpha = clamp((uBaseY - vDispY) / 0.5, 0.0, 1.0) * 0.38; col *= 0.55; }",
    "  gl_FragColor = vec4(col, alpha);",
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

  function torus(cx, cy, cz, R, tube, arcFrom, arcTo, flip, color) {
    var pos = [], norm = [], col = [], idx = [];
    var U = 26, V = 12;
    for (var j = 0; j <= V; j++) {
      var vv = (j / V) * Math.PI * 2, cv = Math.cos(vv), sv = Math.sin(vv);
      for (var i = 0; i <= U; i++) {
        var uu = arcFrom + (arcTo - arcFrom) * (i / U), cu = Math.cos(uu), su = Math.sin(uu);
        pos.push(cx + (R + tube * cv) * cu, cy + (R + tube * cv) * su, cz + tube * sv);
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

  /* curved plaque: a medallion wrapped onto the cup's flared bowl —
     z follows the bowl (flares with y, curves back at the sides) */
  function disc(cx, cy, cz, r, sz, color) {
    var pos = [], norm = [], col = [], idx = [];
    var W = 20, H = 14;
    for (var j = 0; j <= H; j++) {
      var v = j / H, th = v * Math.PI;
      for (var i = 0; i <= W; i++) {
        var u = i / W, ph = u * Math.PI * 2;
        var x = Math.sin(th) * Math.cos(ph), y = Math.cos(th), z = Math.sin(th) * Math.sin(ph);
        var lx = x * r, ly = y * r;
        pos.push(cx + lx, cy + ly, cz + z * r * sz + 0.48 * ly - 0.55 * lx * lx);
        norm.push(x * 0.65, y * 0.65, z);
        col.push(color[0], color[1], color[2]);
      }
    }
    for (var jj = 0; jj < H; jj++) for (var ii = 0; ii < W; ii++) {
      var a = jj * (W + 1) + ii, b = a + W + 1;
      idx.push(a, b, a + 1, b, b + 1, a + 1);
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

  var GOLD = [0.93, 0.72, 0.28], DEEPGOLD = [0.72, 0.50, 0.15], MEDAL = [1.0, 0.84, 0.42];
  function buildTrophyParts() {
    var profile = [
      [0.0, 0.0], [0.52, 0.0], [0.56, 0.05], [0.56, 0.13], [0.32, 0.19], [0.21, 0.28],
      [0.175, 0.52], [0.175, 0.72], [0.28, 0.92], [0.48, 1.16], [0.64, 1.44],
      [0.72, 1.70], [0.74, 1.88], [0.70, 1.92], [0.665, 1.80]
    ];
    var body = merge([
      lathe(profile, 80, GOLD),
      torus(0.50, 1.40, 0, 0.30, 0.06, -Math.PI * 0.46, Math.PI * 0.46, false, GOLD),
      torus(-0.50, 1.40, 0, 0.30, 0.06, Math.PI * 0.54, Math.PI * 1.46, true, GOLD),
      ringY(1.90, 0.715, 0.030, GOLD),
      ringY(0.62, 0.178, 0.020, GOLD)
    ]);
    var plaque = merge([
      disc(0, 1.30, 0.575, 0.26, 0.42, [0.16, 0.11, 0.05]),
      disc(0, 1.30, 0.63, 0.155, 0.5, MEDAL)
    ]);
    return [
      { geom: body, kind: 1.0 },
      { geom: plaque, kind: 2.0 }
    ];
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
    ["uMVP", "uModel", "uModelFull", "uCam", "uLight1", "uLight2", "uKind", "uReflect", "uBaseY"].forEach(function (name) {
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
    var built = kind === "ball" ? [{ geom: buildBall(), kind: 0.0 }] : buildTrophyParts();
    this.parts = built.map(function (part) {
      return {
        kind: part.kind, count: part.geom.idx.length,
        bPos: buffer(part.geom.pos), bNorm: buffer(part.geom.norm),
        bCol: buffer(part.geom.col), bIdx: buffer(part.geom.idx, true)
      };
    });
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
    var rockX = 0;
    if (this.kind === "ball") {
      this.velY += (0.4 * auto - this.velY) * Math.min(1, dt * 1.6);
      if (!this.dragging) this.rotY += this.velY * dt;
      this.rotX += Math.sin(t * 0.0006) * 0.00012 * auto;
    } else {
      this.rotY += 0.55 * dt * auto;
      rockX = Math.sin(t * 0.00045) * 0.16 * auto;
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
    var scale = this.kind === "ball" ? 1 : 0.86;
    var yOff = this.kind === "ball" ? bob : -0.646;
    var effRotX = this.rotX + rockX;
    var model = modelMatrix(0, yOff, 0, effRotX, this.rotY, scale);
    var worldModel = modelMatrix(0, 0, 0, effRotX, this.rotY, 1);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.uniform1f(this.u.uBaseY, -0.645);
    gl.uniform3f(this.u.uCam, 0, 0, dist);
    if (this.kind === "ball") {
      gl.uniform3f(this.u.uLight1, 0.55, 0.85, 0.75);
    } else {
      var la = t * 0.0005;
      gl.uniform3f(this.u.uLight1, Math.cos(la) * 0.62 + 0.3, 0.85, Math.sin(la) * 0.62 + 0.45);
    }
    gl.uniform3f(this.u.uLight2, -0.65, -0.15, 0.45);
    var self = this;
    function drawPass(mFull, mLight, refl) {
      gl.uniformMatrix4fv(self.u.uMVP, false, multiply(proj, multiply(view, mFull)));
      gl.uniformMatrix4fv(self.u.uModel, false, mLight);
      gl.uniformMatrix4fv(self.u.uModelFull, false, mFull);
      gl.uniform1f(self.u.uReflect, refl);
      for (var pi = 0; pi < self.parts.length; pi++) {
        var part = self.parts[pi];
        gl.uniform1f(self.u.uKind, part.kind);
        var binds = [[self.aPos, part.bPos], [self.aNorm, part.bNorm], [self.aCol, part.bCol]];
        for (var bi = 0; bi < binds.length; bi++) {
          if (binds[bi][0] < 0) continue;
          gl.bindBuffer(gl.ARRAY_BUFFER, binds[bi][1]);
          gl.enableVertexAttribArray(binds[bi][0]);
          gl.vertexAttribPointer(binds[bi][0], 3, gl.FLOAT, false, 0, 0);
        }
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, part.bIdx);
        gl.drawElements(gl.TRIANGLES, part.count, gl.UNSIGNED_INT, 0);
      }
    }
    if (this.kind === "trophy") {
      var mFull = Float32Array.from(model); mFull[1] = -mFull[1]; mFull[5] = -mFull[5]; mFull[9] = -mFull[9]; mFull[13] = -mFull[13];
      var mLight = Float32Array.from(worldModel); mLight[1] = -mLight[1]; mLight[5] = -mLight[5]; mLight[9] = -mLight[9]; mLight[13] = -mLight[13];
      gl.depthMask(false);
      drawPass(mFull, mLight, 1.0);
      gl.depthMask(true);
    }
    drawPass(model, worldModel, 0.0);
    if (this.shadowEl && this.kind === "ball") {
      var s = 1 - (bob + 0.055) * 0.55;
      this.shadowEl.style.transform = "translateX(-50%) scaleX(" + s.toFixed(3) + ")";
      this.shadowEl.style.opacity = (0.62 - (bob + 0.055) * 1.4).toFixed(3);
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
