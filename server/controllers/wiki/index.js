import asyncHandler from "express-async-handler";
import { completeJob, ingestFileService,jobStatus,queryWikiService } from "../../services/wiki/index.js";

export const ingestController = asyncHandler(async(req,res)=>{
    
    if(!req.file){
        const error = new Error("No file provided!")
        error.statusCode = 400
        throw error;
    }

    const result = await ingestFileService(req.user.id,req.file);

    res.status(202).json(result);

})


export const queryWikiController = asyncHandler(async(req,res)=>{

    const {question,context} = req.body;

    if(!question){
        const error = new Error("No question provided");
        error.statusCode = 400;
        throw error;
    }

    const result = await queryWikiService(req.user.id, question, context);

    res.status(202).json(result);

})

export const getJobStatusController = asyncHandler(async(req,res)=>{
    const {jobId} = req.params;

    const job = await jobStatus(jobId);

    return res.status(200).json({
        id: job.id,
        status: job.status, 
        filename: job.original_filename,
        markdown_content: job.status === 'completed' ? job.markdown_result : null
    })
})

export const completeJobController = asyncHandler(async(req,res)=>{
    const {jobId} = req.params;
    const { markdown_result,status} = req.body;

    await completeJob(jobId,status,markdown_result);

    res.status(200).json({message:"Job updated successfully"});
})