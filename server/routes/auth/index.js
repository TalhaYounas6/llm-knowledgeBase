import express from "express"
import { loginController, registerController } from "../../controllers/auth/index.js";

const router = express.Router();

router.post('/auth/register',registerController);
router.post('/auth/login',loginController)

export default router;