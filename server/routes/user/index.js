import asyncHandler from "express-async-handler";
import { getUserStatus } from "../../services/user/index.js";

export const getStatusController = asyncHandler(async(req,res)=>{
    const status = await getUserStatus(req.user.id);

    return res.status(200).json(status)

})