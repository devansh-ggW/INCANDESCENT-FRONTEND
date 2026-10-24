"""Static regression checks for INCANDESCENT product UI and chat-only behavior."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
SERVER = (ROOT / "server.py").read_text(encoding="utf-8")
MODELFILE = (ROOT / "Modelfile").read_text(encoding="utf-8")


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


checks = {
    "product keeps its own name": "<title>Incandescent</title>" in HTML,
    "light scheme is requested": 'name="color-scheme" content="light"' in HTML,
    "real favicon is linked": 'href="/incandescent.ico?v=6" type="image/x-icon"' in HTML,
    "assistant uses actual icon": 'src="/incandescent.ico?v=6" alt=""' in HTML,
    "custom AI creation flow exists": 'id="createAiButton"' in HTML and 'id="aiBuilderDialog"' in HTML,
    "Create AI is compact and rectangular": ".create-ai-trigger" in HTML and "height:30px" in HTML and "border-radius:8px" in HTML,
    "one New Chat control remains": len(re.findall(r'id="sidebarNewChat"', HTML)) == 1 and 'id="newConversation"' not in HTML,
    "Create AI sits above New Chat": HTML.index('id="createAiButton"') < HTML.index('id="sidebarNewChat"'),
    "top-right menu button toggles sidebar": 'id="sidebarToggle"' in HTML and "document.body.classList.toggle('sidebar-collapsed')" in HTML,
    "collapsed sidebar is fully hidden": ".sidebar-collapsed .sidebar { display:none" in HTML,
    "send arrow is persistent": 'class="send-arrow"' in HTML and 'class="send-stop"' not in HTML,
    "separate stop control exists": 'id="stopButton"' in HTML and "stopButton.addEventListener('click', () => cancelCurrentRequest())" in HTML,
    "stop control only appears while responding": "stopButton.classList.toggle('visible', sending)" in HTML,
    "stop clears queued follow-ups": "session.queuedMessages.length = 0;" in HTML,
    "streaming turns create assistant placeholders": HTML.count("session.messages.push({ role: 'assistant', content: '' })") == 2,
    "whole response copy button exists": "data-copy-message" in HTML and "copy-response" in HTML,
    "code blocks retain one-click copy": "Copy code" in HTML and "bindCodeButtons(messagesEl)" in HTML,
    "file chooser supports source text and images, not ZIP imports": 'id="attachmentInput"' in HTML and ".png,.jpg,.jpeg,.webp" in HTML and ".zip" not in re.search(r'id="attachmentInput"[^>]*', HTML).group(0),
    "image analysis builds edge and color layers": "buildImageAnalysisLayers" in HTML and "Sobel gradient map" in HTML and "Quantized low-resolution color map" in HTML,
    "image layers are included in model requests": "expandAnalysisAttachments(attachmentDraft)" in HTML and "analysis_layers" in HTML,
    "assistant responses render as chat text": "function renderMessage(item, index)" in HTML and "renderMarkdown(item.content)" in HTML,
    "custom AI names are escaped inside message markup": "escapeHtml(label)" in HTML,
    "attachment size includes derived image layers": "file.analysis_layers.reduce" in HTML and "layer.size" in HTML,
    "generated artifact page is removed": 'id="page-artifacts"' not in HTML and "artifactLibrary" not in HTML,
    "API key UI is removed": "apiKeyDialog" not in HTML and "generateApiKey" not in HTML and "data-api-ai" not in HTML,
    "ZIP upload UI is removed": "uploadProject" not in HTML and "queuedZipUploads" not in HTML and "/api/upload" not in HTML,
    "no experimental local workspace tagline": "Your local AI workspace" not in HTML and "Getting Incandescent ready" not in HTML,
    "no upload-only state remains": "state.uploading" not in HTML and "Loading project…" not in HTML,
    "sidebar sections are independently sized and scrollable": "Stable sidebar geometry" in HTML and "line-height:1.35 !important" in HTML and "overflow-y:auto !important" in HTML,
    "Qt WebEngine can create and clear AI catalog rows": "function clearChildren(element)" in HTML and ".replaceChildren(" not in HTML,
    "conversation heading remains legible": "text-transform:none !important" in HTML and "text-overflow:ellipsis !important" in HTML,
    "AI creator catches modal and save failures": "function showDialogSafely(dialog)" in HTML and "Could not open AI creator:" in HTML,
    "custom AI offers local install and portable export": 'id="aiDeployInstall"' in HTML and 'id="aiDeployExport"' in HTML and "Download portable files" in HTML,
    "custom AI calls both backend deployment actions": "'/api/ai/install'" in HTML and "'/api/ai/export'" in HTML,
    "saved AI rows have a direct install icon": "data-install-ai" in HTML and "Add ' + escapeHtml(profile.name) + ' to Ollama" in HTML,
    "install popup asks for a custom Ollama name": 'id="aiDeployModelName"' in HTML and 'id="aiDeployTagPreview"' in HTML and "e.g. dawg or dig it up" in HTML,
    "custom name and explicit replacement choice are sent to install": "model_name:displayName" in HTML and "replace_existing:$('aiDeployReplaceExisting').checked" in HTML,
    "replacement checkbox is safe by default": 'id="aiDeployReplaceExisting" type="checkbox"' in HTML and "$('aiDeployReplaceExisting').checked = false" in HTML,
    "replacing a named model keeps temporary backup handling": "temporary backup" in SERVER and '"replaced": bool(existing_tag)' in SERVER,
    "AI prompt says not to explain slang unless asked": "Never explain slang unless the user asks what it means" in SERVER,
    "no API-key endpoint remains in backend": "/api/keys" not in SERVER and "v1/chat/completions" not in SERVER,
    "no generated-file service remains in backend": "/api/files/" not in SERVER and "create_artifact" not in SERVER and "def execute_tool" not in SERVER,
    "backend system prompt describes text output": "does not write project files" in SERVER and "provide useful complete code" in SERVER,
    "backend has no generated-file response field": '"files": []' not in SERVER,
    "image analysis routes through vision model": "vision_model_for_request(MODEL)" in SERVER and 'user_turn["images"] = images' in SERVER,
    "model preset uses chat-only rules": "Do not create files" in MODELFILE,
    "legacy file-writing Tkinter agent is removed": not (ROOT / "incandescent_engine.py").exists(),
    "obsolete API guide is removed": not (ROOT / "API_USAGE.md").exists(),
}

# appToast is intentionally created on demand by showToast() rather than in the HTML.
html_ids = re.findall(r'\bid="([^"]+)"', HTML)
static_id_refs = set(re.findall(r"\$\('([^']+)'\)", HTML))
checks["static DOM IDs are unique"] = len(html_ids) == len(set(html_ids))
checks["static element references resolve"] = not (static_id_refs - set(html_ids) - {"appToast"})

for label, passed in checks.items():
    check(passed, label)

print("PASS: professional chat UI, unique New Chat, and fully collapsible sidebar")
print("PASS: stable send arrow, separate stop control, and queued-task cancellation")
print("PASS: one-click response/code copying and safe custom assistant labels")
print("PASS: source/image attachments with layered image preprocessing")
print("PASS: no API-key interface, generated-file UI, or output endpoints")
print("PASS: static DOM integrity and current product-contract checks")
