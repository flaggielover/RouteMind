import type { CustomLayerInterface, Map as MapLibreMap } from "maplibre-gl";
import fragmentShaderSource from "./shaders/mapOpticalLens.frag.glsl?raw";
import vertexShaderSource from "./shaders/mapOpticalLens.vert.glsl?raw";

export const MAP_OPTICAL_LENS_LAYER_ID = "routemind-map-optical-lens";

const LENS_DISTORTION = 1.5;
const MAX_RGB_SHIFT = 0.012;

export interface MapOpticalLensPointerFrame {
  x: number;
  y: number;
  vx: number;
  vy: number;
  viewportWidth: number;
  viewportHeight: number;
  active: boolean;
  reducedMotion: boolean;
}

export interface MapOpticalLensTarget {
  pointer: readonly [number, number];
  lensSize: number;
  rgbShift: number;
  opacity: number;
}

export interface MapOpticalLensDebugState {
  active: boolean;
  distortion: number;
  opacity: number;
  rgbShift: number;
}

interface UniformLocations {
  scene: WebGLUniformLocation | null;
  resolution: WebGLUniformLocation | null;
  pointer: WebGLUniformLocation | null;
  lensSize: WebGLUniformLocation | null;
  distortion: WebGLUniformLocation | null;
  rgbShift: WebGLUniformLocation | null;
  opacity: WebGLUniformLocation | null;
}

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

const smoothstep = (edge0: number, edge1: number, value: number) => {
  const position = clamp((value - edge0) / Math.max(edge1 - edge0, Number.EPSILON), 0, 1);
  return position * position * (3 - 2 * position);
};

export function resolveMapOpticalLensTarget(
  frame: MapOpticalLensPointerFrame,
  drawingBufferWidth: number,
  drawingBufferHeight: number,
): MapOpticalLensTarget {
  const viewportWidth = Math.max(frame.viewportWidth, 1);
  const viewportHeight = Math.max(frame.viewportHeight, 1);
  const scaleX = drawingBufferWidth / viewportWidth;
  const scaleY = drawingBufferHeight / viewportHeight;
  const pixelScale = Math.min(scaleX, scaleY);
  // Keep the square inspection window compact: it is a local optical probe,
  // not a second viewport over the operational world.
  const cssLensSize = clamp(Math.min(viewportWidth, viewportHeight) * 0.058, 34, 48);
  const speed = Math.hypot(frame.vx, frame.vy);
  const velocityResponse = smoothstep(0.4, 24, speed);

  return {
    pointer: [frame.x * scaleX, drawingBufferHeight - frame.y * scaleY],
    lensSize: cssLensSize * pixelScale,
    rgbShift: frame.active && !frame.reducedMotion ? velocityResponse * MAX_RGB_SHIFT : 0,
    opacity: frame.active ? 1 : 0,
  };
}

function requireWebGL2(gl: WebGLRenderingContext | WebGL2RenderingContext) {
  if (!("createVertexArray" in gl)) {
    throw new Error("RouteMind optical lens requires WebGL2");
  }
  return gl as WebGL2RenderingContext;
}

function createShader(gl: WebGL2RenderingContext, type: number, source: string) {
  const shader = gl.createShader(type);
  if (!shader) throw new Error("Unable to allocate optical lens shader");
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const reason = gl.getShaderInfoLog(shader) || "Unknown shader compilation error";
    gl.deleteShader(shader);
    throw new Error(`Unable to compile optical lens shader: ${reason}`);
  }
  return shader;
}

function createProgram(gl: WebGL2RenderingContext) {
  const vertexShader = createShader(gl, gl.VERTEX_SHADER, vertexShaderSource);
  const fragmentShader = createShader(gl, gl.FRAGMENT_SHADER, fragmentShaderSource);
  const program = gl.createProgram();
  if (!program) {
    gl.deleteShader(vertexShader);
    gl.deleteShader(fragmentShader);
    throw new Error("Unable to allocate optical lens program");
  }
  gl.attachShader(program, vertexShader);
  gl.attachShader(program, fragmentShader);
  gl.linkProgram(program);
  gl.deleteShader(vertexShader);
  gl.deleteShader(fragmentShader);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    const reason = gl.getProgramInfoLog(program) || "Unknown program link error";
    gl.deleteProgram(program);
    throw new Error(`Unable to link optical lens program: ${reason}`);
  }
  return program;
}

const approach = (current: number, target: number, elapsed: number, responseMs: number) =>
  current + (target - current) * (1 - Math.exp(-elapsed / responseMs));

export class MapOpticalLensLayer implements CustomLayerInterface {
  readonly id = MAP_OPTICAL_LENS_LAYER_ID;
  readonly type = "custom" as const;
  readonly renderingMode = "2d" as const;

  private map: MapLibreMap | null = null;
  private program: WebGLProgram | null = null;
  private vertexArray: WebGLVertexArrayObject | null = null;
  private vertexBuffer: WebGLBuffer | null = null;
  private captureTexture: WebGLTexture | null = null;
  private uniforms: UniformLocations | null = null;
  private captureWidth = 0;
  private captureHeight = 0;
  private opacity = 0;
  private rgbShift = 0;
  private lastRenderTime = 0;
  private frame: MapOpticalLensPointerFrame = {
    x: 0,
    y: 0,
    vx: 0,
    vy: 0,
    viewportWidth: 1,
    viewportHeight: 1,
    active: false,
    reducedMotion: false,
  };

  setPointerFrame(frame: MapOpticalLensPointerFrame) {
    const previous = this.frame;
    const changed =
      frame.active !== previous.active ||
      frame.reducedMotion !== previous.reducedMotion ||
      Math.abs(frame.x - previous.x) > 0.05 ||
      Math.abs(frame.y - previous.y) > 0.05 ||
      Math.abs(frame.vx - previous.vx) > 0.02 ||
      Math.abs(frame.vy - previous.vy) > 0.02 ||
      Math.abs(frame.viewportWidth - previous.viewportWidth) > 0.5 ||
      Math.abs(frame.viewportHeight - previous.viewportHeight) > 0.5;
    this.frame = frame;
    if (frame.reducedMotion) this.rgbShift = 0;
    const targetOpacity = frame.active ? 1 : 0;
    const settling =
      Math.abs(this.opacity - targetOpacity) > 0.002 || Math.abs(this.rgbShift) > 0.00005;
    if (changed || settling) this.map?.triggerRepaint();
  }

  getDebugState(): MapOpticalLensDebugState {
    return {
      active: this.frame.active,
      distortion: LENS_DISTORTION,
      opacity: this.frame.active ? 1 : this.opacity,
      rgbShift: this.rgbShift,
    };
  }

  onAdd(map: MapLibreMap, context: WebGLRenderingContext | WebGL2RenderingContext) {
    const gl = requireWebGL2(context);
    this.map = map;
    try {
      this.program = createProgram(gl);
      this.vertexArray = gl.createVertexArray();
      this.vertexBuffer = gl.createBuffer();
      this.captureTexture = gl.createTexture();
      if (!this.vertexArray || !this.vertexBuffer || !this.captureTexture) {
        throw new Error("Unable to allocate optical lens WebGL resources");
      }

      gl.bindVertexArray(this.vertexArray);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.vertexBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
      gl.enableVertexAttribArray(0);
      gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
      gl.bindVertexArray(null);
      gl.bindBuffer(gl.ARRAY_BUFFER, null);

      gl.bindTexture(gl.TEXTURE_2D, this.captureTexture);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.bindTexture(gl.TEXTURE_2D, null);

      this.uniforms = {
        scene: gl.getUniformLocation(this.program, "uScene"),
        resolution: gl.getUniformLocation(this.program, "uResolution"),
        pointer: gl.getUniformLocation(this.program, "uPointer"),
        lensSize: gl.getUniformLocation(this.program, "uLensSize"),
        distortion: gl.getUniformLocation(this.program, "uDistortion"),
        rgbShift: gl.getUniformLocation(this.program, "uRgbShift"),
        opacity: gl.getUniformLocation(this.program, "uOpacity"),
      };
    } catch (error) {
      this.dispose(gl);
      throw error;
    }
  }

  render(context: WebGLRenderingContext | WebGL2RenderingContext) {
    const gl = requireWebGL2(context);
    if (
      !this.program ||
      !this.vertexArray ||
      !this.captureTexture ||
      !this.uniforms ||
      gl.drawingBufferWidth <= 0 ||
      gl.drawingBufferHeight <= 0
    ) {
      return;
    }

    const now = globalThis.performance?.now() ?? Date.now();
    const elapsed = this.lastRenderTime ? clamp(now - this.lastRenderTime, 1, 64) : 16;
    this.lastRenderTime = now;
    const target = resolveMapOpticalLensTarget(
      this.frame,
      gl.drawingBufferWidth,
      gl.drawingBufferHeight,
    );
    this.opacity = approach(this.opacity, target.opacity, elapsed, target.opacity ? 58 : 92);
    this.rgbShift = approach(this.rgbShift, target.rgbShift, elapsed, target.rgbShift ? 24 : 90);
    if (this.opacity < 0.002 && target.opacity === 0) {
      this.opacity = 0;
      this.rgbShift = 0;
      return;
    }

    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, this.captureTexture);
    if (
      this.captureWidth !== gl.drawingBufferWidth ||
      this.captureHeight !== gl.drawingBufferHeight
    ) {
      this.captureWidth = gl.drawingBufferWidth;
      this.captureHeight = gl.drawingBufferHeight;
      gl.texImage2D(
        gl.TEXTURE_2D,
        0,
        gl.RGBA,
        this.captureWidth,
        this.captureHeight,
        0,
        gl.RGBA,
        gl.UNSIGNED_BYTE,
        null,
      );
    }
    gl.copyTexSubImage2D(gl.TEXTURE_2D, 0, 0, 0, 0, 0, this.captureWidth, this.captureHeight);

    gl.useProgram(this.program);
    gl.bindVertexArray(this.vertexArray);
    gl.disable(gl.DEPTH_TEST);
    gl.disable(gl.CULL_FACE);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    gl.uniform1i(this.uniforms.scene, 0);
    gl.uniform2f(this.uniforms.resolution, this.captureWidth, this.captureHeight);
    gl.uniform2f(this.uniforms.pointer, target.pointer[0], target.pointer[1]);
    gl.uniform1f(this.uniforms.lensSize, target.lensSize);
    gl.uniform1f(this.uniforms.distortion, LENS_DISTORTION);
    gl.uniform1f(this.uniforms.rgbShift, this.rgbShift);
    gl.uniform1f(this.uniforms.opacity, this.opacity);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    gl.bindVertexArray(null);
    gl.bindTexture(gl.TEXTURE_2D, null);

    if (
      Math.abs(this.opacity - target.opacity) > 0.002 ||
      Math.abs(this.rgbShift - target.rgbShift) > 0.00005
    ) {
      this.map?.triggerRepaint();
    }
  }

  onRemove(_map: MapLibreMap, context: WebGLRenderingContext | WebGL2RenderingContext) {
    this.dispose(requireWebGL2(context));
  }

  private dispose(gl: WebGL2RenderingContext) {
    if (this.captureTexture) gl.deleteTexture(this.captureTexture);
    if (this.vertexBuffer) gl.deleteBuffer(this.vertexBuffer);
    if (this.vertexArray) gl.deleteVertexArray(this.vertexArray);
    if (this.program) gl.deleteProgram(this.program);
    this.captureTexture = null;
    this.vertexBuffer = null;
    this.vertexArray = null;
    this.program = null;
    this.uniforms = null;
    this.captureWidth = 0;
    this.captureHeight = 0;
    this.map = null;
  }
}
