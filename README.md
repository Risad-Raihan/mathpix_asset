```
Convert an entire PDF to Markdown with Mathpix Markdown (MMD) via
Mathpix's official Python SDK (mpxpy).
• Saves `.md` output alongside the source PDF
• Wraps every inline or display equation in $ … $ (handled automatically
by Mathpix)
• Downloads any extracted diagram/table images into a folder named
`<pdf-stem>_assets/`
• Requires: pip install mpxpy >= 0.4.0
```
