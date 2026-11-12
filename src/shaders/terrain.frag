precision highp float;
uniform sampler2D uMask;
uniform sampler2D uCrustAlbedo;
uniform sampler2D uCrustNormal;
uniform sampler2D uGranularAlbedo;
uniform sampler2D uGranularNormal;
uniform float uWetness;
uniform float uExtent;
uniform vec3 uSun;
varying vec3 vWorld;
varying vec3 vNormal;
varying vec2 vUv;
varying float vAO;
varying float vWet;

void main(void) {
    vec2 uv = (vUv * 255.0 + 0.5) / 256.0;
    vec4 mask = texture2D(uMask, uv);
    vec2 detail = vec2(vWorld.x, vWorld.z+vWorld.y*0.65) / 480.0;
    vec2 second = vec2(-detail.y, detail.x) * 0.37 + 0.23;
    float crustDetail = mix(texture2D(uCrustAlbedo, detail).r,
                            texture2D(uCrustAlbedo, second).r, 0.35);
    float granularDetail = mix(texture2D(uGranularAlbedo, detail).r,
                               texture2D(uGranularAlbedo, second).r, 0.35);
    vec3 crustNormal = mix(texture2D(uCrustNormal, detail).xyz,
                           texture2D(uCrustNormal, second).xyz, 0.25) * 2.0 - 1.0;
    vec3 grainNormal = mix(texture2D(uGranularNormal, detail).xyz,
                           texture2D(uGranularNormal, second).xyz, 0.25) * 2.0 - 1.0;
    float crust = smoothstep(0.35, 0.80, mask.r + (granularDetail-0.75));
    vec3 granular = vec3(0.345, 0.318, 0.275) * (0.75+0.35*granularDetail);
    vec3 ochre = mix(vec3(0.690, 0.541, 0.333), vec3(0.761, 0.647, 0.478), crustDetail);
    vec3 albedo = mix(granular, ochre*crustDetail, crust);
    albedo = mix(albedo, vec3(0.741, 0.702, 0.627), mask.b*0.40);
    albedo *= mix(0.88, 1.1, mask.g);
    vec3 geometric = normalize(vNormal);
    vec3 tangent = normalize(vec3(geometric.y, -geometric.x, 0.0001));
    vec3 bitangent = normalize(cross(geometric, tangent));
    vec3 detailNormal = normalize(mix(grainNormal, crustNormal, crust));
    vec3 n = normalize(mat3(tangent, bitangent, geometric) * detailNormal);
    float sunlight = max(dot(n, uSun), 0.0);
    float ao = mix(0.5, 1.0, clamp(vAO, 0.0, 1.0));
    vec3 illumination = (vec3(0.64,0.64,0.64)+vec3(0.85,0.79,0.68)*sunlight)*ao;
    vec3 color = albedo*sqrt(illumination);
    color *= 1.0 - uWetness*0.16*(1.0-crust);
    color *= 1.0 - vWet*uWetness*0.16;
    color += vec3(0.035, 0.031, 0.026)*vWet*uWetness*sunlight;
    vec2 marks = texture2D(uCrustAlbedo, vWorld.xz/2400.0).gb;
    color = mix(color, vec3(0.57,0.28,0.12), marks.x*.7);
    color = mix(color, vec3(0.8,0.77,0.69), marks.y*.3);
    float edge = smoothstep(uExtent*.46, uExtent*.5, max(abs(vWorld.x),abs(vWorld.z)));
    color = mix(color, vec3(.898,.875,.827), edge);
    gl_FragColor = vec4(color, 1.0);
}
