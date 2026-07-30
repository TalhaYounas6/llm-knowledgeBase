import asyncHandler from "express-async-handler";
import { changeApiKey, getUserStatus } from "../../services/user/index.js";

export const getStatusController = asyncHandler(async(req,res)=>{
    const status = await getUserStatus(req.user.id);

    return res.status(200).json(status)

})

export const changeApiKeyController = asyncHandler(async(req,res)=>{
    const customKey = req.body;

    if(!customKey){
        const error = new Error("No custom API Key provided!");
        error.statusCode = 400;
        throw error;
    }

    const result = await changeApiKey(req.user.id,customKey);

    return res.status(200).json(result);
})