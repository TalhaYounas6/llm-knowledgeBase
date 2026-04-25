import express from "express"
import { changeApiKeyController, getStatusController } from "../../controllers/user/index.js";
import {protect} from "../../middlewares/auth.middleware.js"

const router = express.Router();

router.get('/user/get-status',protect,getStatusController);
router.post('/user/key',protect,changeApiKeyController);

export default router;
