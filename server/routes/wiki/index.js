import express from "express"
import { protect } from "../../middlewares/auth.middleware.js";
import { completeJobController, deleteJobController, getJobStatusController, ingestController, queryWikiController } from "../../controllers/wiki/index.js";
import { upload } from "../../utils/multer.js";
import { validateUpload } from "../../middlewares/validateFile.middleware.js";

const router = express.Router();

router.post('/wiki/ingest',protect,upload.single('document'),validateUpload,ingestController);
router.post('/wiki/query',protect,queryWikiController);
router.get('/wiki/job/:jobId',protect,getJobStatusController);
router.delete('/wiki/delete-job/:jobId',protect,deleteJobController);  
// for the python worker
router.put('/wiki/internal/job/:jobId',completeJobController);

export default router;