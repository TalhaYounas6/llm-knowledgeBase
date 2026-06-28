import path from "path";

const ALLOWED_EXTENSIONS = new Set([".pdf", ".txt", ".ppt", ".docx", ".md"]);
const MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB

export function validateUpload(req, res, next) {
  if (!req.file) {
    return res.status(400).json({ message: "No file uploaded." });
  }

  const ext = path.extname(req.file.originalname).toLowerCase();

  if (!ALLOWED_EXTENSIONS.has(ext)) {
    return res.status(400).json({
      message: `Unsupported file type: ${ext || "no extension"}. Allowed types are .pdf, .txt, .ppt, .docx. , .md`,
    });
  }

  const fileSize = req.file.size ?? req.file.buffer?.length ?? 0;
  if (fileSize > MAX_UPLOAD_SIZE_BYTES) {
    return res.status(400).json({
      message: "File too large. Maximum allowed size is 5 MB.",
    });
  }

  next();
}