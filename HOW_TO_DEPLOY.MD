# WaveLoft Backend (AWS SAM) — Deploy Guide (Windows / PowerShell)

This repository deploys the WaveLoft backend using **AWS SAM + CloudFormation** to AWS.

## Project constants
- **Stack name:** `music-api-stack`
- **Region:** `eu-north-1`
- **AWS SSO profile:** `pablito`
- **SSO Start URL (console):** `https://d-c3670ed5fb.awsapps.com/start/`
- **API URL (from stack output):** `https://2vbswqksvg.execute-api.eu-north-1.amazonaws.com/Prod`

---

## Console access (SSO)
Do **not** use the normal AWS console login (root/IAM MFA).

1. Open: `https://d-c3670ed5fb.awsapps.com/start/`
2. Go to **Accounts** → expand **WaveLoft** → select **AdministratorAccess** → **Management console**

---

## Prerequisites (one-time)
Install:
- **AWS CLI v2**
- **AWS SAM CLI**
- **Python 3.12**

Verify:
```powershell

.\.venv312\Scripts\Activate.ps1; python --version; sam build



aws --version
sam --version
py -3.12 --version
One-time setup (recommended): Python 3.12 virtualenv
SAM uses python from PATH. On Windows, python may point to 3.11 even if py -3.12 exists, causing sam build to fail for runtime python3.12.

Create venv once (from repo root):

py -3.12 -m venv .venv312
If activation is blocked:

Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
Daily deploy workflow (copy/paste)
1) Activate venv (must show Python 3.12.x)
.\.venv312\Scripts\Activate.ps1
python --version
2) Login to AWS SSO (CLI)
aws sso login --profile pablito
3) Build
sam build
4) Deploy
CloudFormation requires both IAM capabilities:

sam deploy --profile pablito --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM
If you need to re-run guided prompts (rare):

sam deploy --guided --profile pablito
Fast “all-in-one” command
.\.venv312\Scripts\Activate.ps1; aws sso login --profile pablito; sam build; sam deploy --profile pablito --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM
Common problems & fixes
A) PythonPipBuilder:Validation ... runtime: python3.12 ... Do you have python3.12 on your PATH?
Cause: python resolves to Python 3.11.
Fix:

.\.venv312\Scripts\Activate.ps1
python --version
sam build
Alternative (requires Docker):

sam build --use-container
B) The config profile (admin-user) could not be found
Cause: samconfig.toml references a profile that does not exist on your machine.
Fix: always pass the correct profile:

sam deploy --guided --profile pablito
or:

sam deploy --profile pablito --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM
Optional permanent fix: edit samconfig.toml and set:

profile = "pablito"
C) Requires capabilities : [CAPABILITY_NAMED_IAM]
Cause: the template creates named IAM roles/policies.
Fix:

sam deploy --profile pablito --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM
Optional permanent fix: ensure samconfig.toml includes:

capabilities = "CAPABILITY_IAM CAPABILITY_NAMED_IAM"
D) ResourceNotFoundException ... Function not found: ...:function:UpdateStatsFunction
Important: UpdateStatsFunction / GetDueTracksFunction are logical IDs.
The real Lambda names are stack-generated (e.g. music-api-stack-UpdateStatsFunction-XXXX).

Get the real Lambda (physical) name from CloudFormation:

UpdateStats:

$fn = aws cloudformation list-stack-resources --stack-name music-api-stack --region eu-north-1 --profile pablito --query "StackResourceSummaries[?LogicalResourceId=='UpdateStatsFunction'].PhysicalResourceId" --output text
aws lambda get-function --function-name $fn --region eu-north-1 --profile pablito --query "Configuration.{FunctionName:FunctionName,LastModified:LastModified,RevisionId:RevisionId}" --output table
GetDueTracks:

$fn = aws cloudformation list-stack-resources --stack-name music-api-stack --region eu-north-1 --profile pablito --query "StackResourceSummaries[?LogicalResourceId=='GetDueTracksFunction'].PhysicalResourceId" --output text
aws lambda get-function --function-name $fn --region eu-north-1 --profile pablito --query "Configuration.{FunctionName:FunctionName,LastModified:LastModified,RevisionId:RevisionId}" --output table
Verify deployment outputs
aws cloudformation describe-stacks --stack-name music-api-stack --region eu-north-1 --profile pablito --query "Stacks[0].Outputs" --output table
Logs (tail)
GetDueTracks logs (resolve physical function name automatically):

$fn = aws cloudformation list-stack-resources --stack-name music-api-stack --region eu-north-1 --profile pablito --query "StackResourceSummaries[?LogicalResourceId=='GetDueTracksFunction'].PhysicalResourceId" --output text
aws logs tail "/aws/lambda/$fn" --follow --region eu-north-1 --profile pablito
UpdateStats logs:

$fn = aws cloudformation list-stack-resources --stack-name music-api-stack --region eu-north-1 --profile pablito --query "StackResourceSummaries[?LogicalResourceId=='UpdateStatsFunction'].PhysicalResourceId" --output text
aws logs tail "/aws/lambda/$fn" --follow --region eu-north-1 --profile pablito
Notes about dependencies (requirements.txt)
If a Lambda needs Python dependencies, SAM expects a requirements.txt inside that function’s CodeUri folder.

If you see:

requirements.txt file not found. Continuing the build without dependencies.
That is fine only if that function truly has no third-party deps.