"""Prepare a clean hosted mobile build; does not deploy or include credentials."""
import argparse,json,shutil
from pathlib import Path
from urllib.parse import urlparse
parser=argparse.ArgumentParser()
parser.add_argument('--url',required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
url=urlparse(args.url)
if url.scheme!='https' or not url.netloc or url.username or url.password or url.query or url.fragment:
    parser.error('Use an HTTPS service endpoint without credentials or query parameters')
root=Path(__file__).resolve().parents[1]
out=args.output.resolve()
if out==root or root in out.parents:
    parser.error('Output must be outside the source repository')
out.mkdir(parents=True,exist_ok=True)
shutil.copy2(root/'mobile/index.html',out/'index.html')
(out/'shared').mkdir(exist_ok=True)
shutil.copy2(root/'shared/sange-core.js',out/'shared/sange-core.js')
shutil.copy2(root/'shared/sange-token.js',out/'shared/sange-token.js')
(out/'shared/service-config.js').write_text('globalThis.SANGE_SERVICE_URL = '+json.dumps(args.url)+';\n',encoding='utf-8')
shutil.copy2(root/'sync-worker/src/index.js',out/'_worker.js')
print('Prepared hosted edition: empty initial lists, embedded endpoint, no tokens or device profile.')
