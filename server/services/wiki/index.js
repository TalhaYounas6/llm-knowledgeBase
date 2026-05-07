import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { User, IngestJob } = require("../../models/index.cjs");
import { getQueueChannel } from '../../config/rabbitMqueue.js';
import { model } from '../../config/gemini.js';



export const ingestFileService = async (userId, file) => {
    // 1. Increment user's usage quota in DB
    const user = await User.findByPk(userId);

    if (user.tier =='free' && user.requests_today>=user.daily_limit){
        throw new Error("Monthly quota exceeded")
    }

    user.requests_today = user.requests_today + 1;
    await user.save()
    // 2. Add job to IngestJobs table (status: 'pending')
    const newJob = await IngestJob.create({
        userId : user.id,
        original_filename : file.originalname,
        status : "pending"
    })
    // 3. Talk to RabbitMQ (Send ticket with file.path and job.id)

    const queue = await getQueueChannel();

    const jobTicket = {
        userId : user.id,
        jobId: newJob.id,
        filePath: file.path,
        original_filename: file.originalname,
    }

    queue.sendToQueue('pdf_jobs',Buffer.from(JSON.stringify(jobTicket)),{ persistent: true});
    // 4. Return job details so the Controller can send a 202 response

    return {
        message : "File queued for processing",
        jobId : newJob.id,
        fileName: file.originalname,
    };
}

export const queryWikiService = async (userId, question, localContext) => {
    // 1. Increment user's usage quota
    const user = await User.findByPk(userId);
    if(!user) throw new Error("User not found");

    if (user.tier == "free" && user.requests_today >= user.daily_limit){
        throw new Error("Monthly quota exceeded");
    }

    const prompt = `
    You are a personal knowledge assistant. Below is the entire context of the user's personal wiki notes.
    Use this context to answer the question as accurately as possible. 
    If the answer isn't in the context, say you don't know. Do not make up information or try to create information
    that is not in the context.

    CONTEXT:
    ${localContext}

    QUESTION:
    ${question}
    `;

    try {

        const result = await model.generateContent(prompt);
        const response = await result.response;
        const text = response.text();

        user.requests_today = user.requests_today + 1;
        await user.save();

        return {
            answer: text,
            status : "success"
        }
        
    } catch (error) {
        console.error("Gemini Query Error:", error);
        throw new Error("AI failed to process your question.");
    }

}

export const jobStatus = async(jobId,userId)=>{

    const job = await IngestJob.findOne({where:{id:jobId,userId:userId}});

    if(!job){
        throw new Error("No job exists!")
    }


    // if (job.status === 'completed' || job.status === 'failed') {
    //     await IngestJob.destroy({ where: { id: job.id } });
    // }

    return job;
}


export const completeJob = async(id,status,markdown_result)=>{

    const job = await IngestJob.findOne({where:{id:id}});

    if(!job){
        throw new Error("No job exists.")
    }

    job.status= status;
    job.markdown_result = markdown_result;

    await job.save();
    
}
