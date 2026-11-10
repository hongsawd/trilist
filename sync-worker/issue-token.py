"""Create a token and registration SQL outside the repository; never print the token."""
import argparse, hashlib, json, secrets, time, uuid
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--private-dir',type=Path,required=True)
args=parser.parse_args()
target=args.private_dir.resolve()
repo=Path(__file__).resolve().parents[1]
if target==repo or repo in target.parents:
    parser.error('Choose a private directory outside the source repository')
target.mkdir(parents=True,exist_ok=True)
owner='user-'+uuid.uuid4().hex
token=secrets.token_urlsafe(32)
digest=hashlib.sha256(token.encode()).hexdigest()
(target/(owner+'.json')).write_text(json.dumps({'owner':owner,'token':token},indent=2),encoding='utf-8')
(target/(owner+'.sql')).write_text("INSERT INTO sync_users(token_sha256,owner,enabled,created_at) VALUES('%s','%s',1,%d);\n"%(digest,owner,int(time.time()*1000)),encoding='utf-8')
print('Created token and registration SQL in the private directory. Token not printed.')
