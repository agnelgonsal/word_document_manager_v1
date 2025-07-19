from fastapi.responses import FileResponse
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os, mammoth, uuid
from docx import Document

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")
STORAGE = "storage"
os.makedirs(STORAGE, exist_ok=True)

# In-memory store
documents = {}

@app.get("/", response_class=HTMLResponse)
def ui_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "documents": documents})

@app.post("/documents")
def create_doc(name: str = Form(...), content: str = Form("")):
    doc_id = str(uuid.uuid4())
    path = os.path.join(STORAGE, f"{doc_id}.docx")
    doc = Document()
    doc.add_paragraph(content)
    doc.save(path)
    documents[doc_id] = {"name": name, "path": path}
    return RedirectResponse(url="/", status_code=303)

@app.get("/documents/{doc_id}", response_class=HTMLResponse)
def edit_page(request: Request, doc_id: str):
    meta = documents.get(doc_id)
    if not meta:
        return HTMLResponse("Not found", status_code=404)
    with open(meta["path"], "rb") as f:
        result = mammoth.convert_to_html(f)
    return templates.TemplateResponse("index.html", {"request": request, "documents": documents, "edit_id": doc_id, "edit_name": meta["name"], "edit_content": result.value})

@app.post("/documents/{doc_id}/update")
def update_doc(doc_id: str, name: str = Form(...), content: str = Form(...)):
    meta = documents.get(doc_id)
    if not meta:
        return HTMLResponse("Not found", status_code=404)
    meta["name"] = name
    doc = Document()
    doc.add_paragraph(content)
    doc.save(meta["path"])
    return RedirectResponse(url="/", status_code=303)

@app.get("/documents/{doc_id}/delete")
def delete_doc(doc_id: str):
    meta = documents.pop(doc_id, None)
    if meta:
        os.remove(meta["path"])
    return RedirectResponse(url="/", status_code=303)

@app.post("/upload")
def upload_doc(file: UploadFile = File(...)):
    doc_id = str(uuid.uuid4())
    path = os.path.join(STORAGE, f"{doc_id}.docx")
    with open(path, "wb") as f:
        f.write(file.file.read())
    documents[doc_id] = {"name": file.filename, "path": path}
    return RedirectResponse(url="/", status_code=303)

@app.get("/documents/{doc_id}/download")
def download_doc(doc_id: str):
    meta = documents.get(doc_id)
    if not meta:
        return JSONResponse(status_code=404, content={"error": "not found"})
    filename = meta["name"] if meta["name"].endswith(".docx") else meta["name"] + ".docx"
    return FileResponse(meta["path"], media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename=filename)
