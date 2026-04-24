import asyncHandler from "express-async-handler";
import { ingestFileService,queryWikiService } from "../../services/wiki/index.js";

export const ingestController = asyncHandler(async(req,res)=>{
    
    if(!req.file){
        const error = new Error("No file provided!")
        error.statusCode = 400
        return next(error);
    }

    const result = await ingestFileService(req.user.id,req.file);

    res.status(202).json(result);

})


export const queryWikiController = asyncHandler(async(req,res)=>{

    const {question,context} = req.body;

    if(!question){
        const error = new Error("No question provided");
        error.statusCode = 400;
        return next(error);
    }

    const result = await queryWikiService(req.user.id, question, context);

    res.status(202).json(result);

})