import asyncHandler from "express-async-handler";
import { completeJob, deleteJob, ingestFileService,jobStatus,queryWikiService } from "../../services/wiki/index.js";
import { error } from "console";

export const ingestController = asyncHandler(async(req,res)=>{
    
    if(!req.file){
        const error = new Error("No file provided!")
        error.statusCode = 400
        throw error;
    }
    
    const {schemaText, indexText,logTail} = req.body;
    
    const result = await ingestFileService(req.user.id,req.file,schemaText,indexText,logTail);

    res.status(202).json(result);

})


export const queryWikiController = asyncHandler(async (req, res) => {
    const { question, indexText, schemaText, pageContents } = req.body;

    if (!question) {
        const error = new Error("No question provided");
        error.statusCode = 400;
        throw error;
    }

    if (!indexText) {
        const error = new Error("No wiki index provided");
        error.statusCode = 400;
        throw error;
    }

    const result = await queryWikiService(
        req.user.id,
        question,
        indexText,
        schemaText || "",
        pageContents || {}
    );

    res.status(200).json(result);
});

export const getJobStatusController = asyncHandler(async(req,res)=>{
    const {jobId} = req.params;

    const job = await jobStatus(jobId,req.user.id);
    const jobData = job.markdown_result || {};

    return res.status(200).json({
        id: job.id,
        status: job.status, 
        filename: job.original_filename,
        markdown_content: jobData,
        stage: jobData.stage ?? null,
        stage_message: jobData.stage_message ?? null,
        error_message: job.error_message ?? null
    })
})

export const completeJobController = asyncHandler(async(req,res)=>{
    const {jobId} = req.params;
    const { plan,status,error,stage,stage_message} = req.body;

    await completeJob(jobId,status,plan,error,stage,stage_message);

    res.status(200).json({message:"Job updated successfully"});
})

export const deleteJobController = asyncHandler(async(req,res)=>{
    const {jobId} = req.params;
    
    await deleteJob(jobId,req.user.id);

    res.status(200).json({message:"Job deleted successfully after finalization"});
})
