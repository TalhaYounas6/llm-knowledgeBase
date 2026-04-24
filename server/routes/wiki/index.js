import express from "express"
import { protect } from "../../middlewares/auth.middleware.js";
import { ingestController, queryWikiController } from "../../controllers/wiki/index.js";
import { upload } from "../../utils/multer.js";

const router = express.Router();

router.post('/ingest',protect,upload.single('document'),ingestController);
router.post('/query',protect,queryWikiController)

export default router;