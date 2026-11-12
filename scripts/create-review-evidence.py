"""Assemble local evidence without altering the reference or captured images."""
import argparse
import html
import json
from pathlib import Path

import numpy as np
from PIL import Image

parser = argparse.ArgumentParser()
parser.add_argument('directory', type=Path)
parser.add_argument('--summary-only',action='store_true')
args = parser.parse_args()
root = args.directory
trace = json.loads((root/'trace.json').read_text())
network = json.loads((root/'first-view.json').read_text())
summary = {key: trace[key] for key in ['capturedAt','browser','renderer','viewport','renderResolution',
    'valid','reasons','durationMs','fps','p95Ms','within16_7Percent','peakDraws','peakGpuBytes','budgetsPass']}
summary['capture']=trace.get('capture',{'screencast':'unknown'})
summary['firstViewBytes'] = network['totalTransferred']
summary['qualification'] = 'Desktop browser evidence. Phone viewport emulation, where used, is not physical phone qualification.'
(root/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
if args.summary_only:
    print(root/'summary.json')
    raise SystemExit(0)
reference = Path('docs/reference/relief-pfyffer.png')
# Fixed material regions: all pixels contribute; no search toward target colours.
source_regions=[('ochre',(590,345,630,385)),('tan crust',(380,385,420,425)),
 ('dark granular',(175,580,215,620)),('mid grey-brown',(165,685,205,725)),
 ('dust',(50,65,90,105)),('water',(1005,385,1045,425))]
render_regions=[('tan crust',(145,475,185,515)),('granular bank',(365,560,405,600)),
 ('water',(1515,620,1555,660))]
samples=[]
for path,regions in [(reference,source_regions),(root/'sanchez-reservoir-terrain.png',render_regions)]:
    with Image.open(path) as source:
        pixels=np.asarray(source.convert('RGB'),dtype='float32')
    for label,roi in regions:
        x0,y0,x1,y1=roi
        patch=pixels[y0:y1,x0:x1]
        rgb=np.rint(patch.mean(axis=(0,1))).astype(int).tolist()
        luma=patch@np.array([.2126,.7152,.0722])
        samples.append({'image':str(path),'region':label,'x':(x0+x1)//2,'y':(y0+y1)//2,
          'roi':roi,'mean_rgb':rgb,'luma_p10_p50_p90':np.percentile(luma,[10,50,90]).round(1).tolist(),
          'hex':'#'+''.join(f'{channel:02X}' for channel in rgb)})
(root/'swatches.json').write_text(json.dumps({'method':'Fixed 40×40 material-region means and luminance percentiles; no target-colour search. Photographed/rendered lighting retained; not a calibrated albedo measurement',
                                              'samples':samples},indent=2)+'\n')
rows = ''.join(f'<tr><td>{html.escape(item["region"])}</td><td>{"Reference" if item["image"]==str(reference) else "Render"}</td><td>{item["x"]}, {item["y"]}</td><td><span style="background:{item["hex"]};display:inline-block;width:2em;height:1em"></span> {item["hex"]}</td></tr>' for item in samples)
views = [('Culebra range','culebra-range'),('Rio Grande gorge','rio-grande-gorge'),
         ('Sanchez Reservoir','sanchez-reservoir'),('Valley fields','valley-fields')]
figures = ''.join(f'<section><h2>{name}</h2><div class="pair"><figure><img src="../../docs/reference/relief-pfyffer.png" alt="Relief Pfyffer style reference"><figcaption>Style authority: saved photograph</figcaption></figure><figure><img src="{file}-terrain.png" alt="Rendered {name}"><figcaption>San Luis · fixed view · {trace["renderResolution"]}</figcaption></figure></div></section>' for name,file in views)
criteria = [('S1','Rounded, irregular clods and abrupt water banks','Further morphology review: ridges remain smoother than the photograph.'),
 ('S2','Ochre convex crust / dark pitted faces','Review material split and grain irregularity at close range.'),
 ('S3','Pale upward dust','Review dust placement and saturation.'),
 ('S4','Matte painted water, rim, grain, restrained shimmer','Review stills and clip; check every shoreline.'),
 ('S5','Sparse rust flecks and pale strands','Review scale and legibility; no roads/buildings are modelled.'),
 ('S6','Warm daylight, crevices, low oblique view','Review photographic read and AO strength.'),
 ('S7','Muted source palette','Review sampled patches; lighting differs and samples are not albedo measurements.')]
checks = ''.join(f'<tr><td>{code}</td><td>{name}</td><td>OPEN — {note}</td></tr>' for code,name,note in criteria)
page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>San Luis reference review</title><style>
body{{max-width:1500px;margin:2rem auto;padding:0 1rem;background:#e5dfd3;color:#302b24;font:17px/1.5 system-ui}}h1,h2{{font-family:Georgia,serif}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}figure{{margin:0}}img,video{{width:100%;display:block}}figcaption{{font-size:.85rem}}table{{border-collapse:collapse;width:100%;margin:1rem 0}}td,th{{padding:.6rem;border-bottom:1px solid #b6ac99;text-align:left}}pre{{white-space:pre-wrap}}@media(max-width:700px){{.pair{{grid-template-columns:1fr}}}}
</style><h1>San Luis / Relief Pfyffer</h1><p>Local review evidence. The source photograph is authoritative. Visual sign-off and physical phone qualification remain open.</p>
<p>PlayCanvas 2.24.0 · WebGL2 · fixed SE sun · no real-time shadows or post-processing. Captured {html.escape(trace['capturedAt'])}.</p>
<img src="overview-terrain.png" alt="Full San Luis diorama overview">{figures}
<h2>Water motion</h2><video controls loop muted src="water-shimmer.webm"></video><p>Eight-second canvas capture. Judge glints in motion, separately from performance recordings.</p>
<h2>Style acceptance</h2><table><tr><th>Criterion</th><th>Required cue</th><th>Status</th></tr>{checks}</table>
<h2>Pixel samples</h2><p>Fixed 40 × 40 region means; every pixel contributes. The bounds and luminance percentiles are in swatches.json. No search toward target colours is used. Photographed light is retained; this is a comparison aid, not a calibrated albedo match.</p><table><tr><th>Region</th><th>Image</th><th>Centre</th><th>Mean</th></tr>{rows}</table>
<h2>Desktop measurement</h2><pre>{html.escape(json.dumps(summary,indent=2))}</pre><p>Full timing, network and browser records are alongside this page. Desktop results cannot establish either target phone budget.</p></html>'''
(root/'index.html').write_text(page)
print(root/'index.html')
