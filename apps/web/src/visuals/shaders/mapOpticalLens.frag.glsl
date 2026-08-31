#version 300 es

precision highp float;

uniform sampler2D uScene;
uniform vec2 uResolution;
uniform vec2 uPointer;
uniform float uLensSize;
uniform float uDistortion;
uniform float uRgbShift;
uniform float uOpacity;

in vec2 vUv;
out vec4 fragColor;

// CC Lens transform adapted from the MIT-licensed Codrops reference implementation.
float getCCLensScale(float distortion, float radius2) {
  if (distortion >= 0.0) return 1.0 + distortion * radius2;
  return 1.0 / (1.0 - distortion * radius2);
}

vec2 getCCLensUv(vec2 uv, float distortion) {
  vec2 centeredUv = uv - 0.5;
  float radius2 = dot(centeredUv, centeredUv);
  float lensScale = getCCLensScale(distortion, radius2);
  vec2 distortedUv = centeredUv * lensScale + 0.5;
  vec2 distortionOffset = distortedUv - uv;
  return uv - distortionOffset;
}

vec2 sceneUv(vec2 localUv) {
  return uPointer / uResolution + (localUv - 0.5) * (uLensSize / uResolution);
}

float roundedSquareDistance(vec2 uv) {
  const float radius = 0.025;
  vec2 q = abs(uv - 0.5) - vec2(0.5 - radius);
  return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - radius;
}

void main() {
  vec2 squareUv = (gl_FragCoord.xy - uPointer) / uLensSize + 0.5;
  float squareDistance = roundedSquareDistance(squareUv);
  float antialiasWidth = max(fwidth(squareDistance), 0.0015);
  float squareMask = 1.0 - smoothstep(-antialiasWidth, antialiasWidth, squareDistance);
  if (squareMask <= 0.001 || uOpacity <= 0.001) discard;

  vec2 distortedUv = getCCLensUv(squareUv, uDistortion);
  vec2 channelDirection = (squareUv - 0.5) * 2.0;
  vec2 redUv = sceneUv(distortedUv + channelDirection * uRgbShift);
  vec2 greenUv = sceneUv(distortedUv);
  vec2 blueUv = sceneUv(distortedUv - channelDirection * uRgbShift);

  vec3 opticalColor = vec3(
    texture(uScene, clamp(redUv, 0.0, 1.0)).r,
    texture(uScene, clamp(greenUv, 0.0, 1.0)).g,
    texture(uScene, clamp(blueUv, 0.0, 1.0)).b
  );

  float luminance = dot(opticalColor, vec3(0.2126, 0.7152, 0.0722));
  opticalColor = mix(vec3(luminance), opticalColor, 1.08);
  opticalColor = (opticalColor - 0.5) * 1.055 + 0.525;

  float edgeBand = 1.0 - smoothstep(0.0, 0.012, abs(squareDistance));
  vec3 edgeColor = vec3(0.54, 0.72, 0.70);
  opticalColor = mix(opticalColor, edgeColor, edgeBand * 0.34);

  float alpha = squareMask * uOpacity;
  fragColor = vec4(clamp(opticalColor, 0.0, 1.0) * alpha, alpha);
}
