import express from "express"
import { getStatusController } from "../../controllers/user/index.js";
import {protect} from "../../middlewares/auth.middleware.js"

const router = express.Router();

router.get('/get-status',protect,getStatusController);

export default router;
