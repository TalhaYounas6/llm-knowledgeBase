import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { User, IngestJob } = require("../../models/index.cjs");
import { getQueueChannel } from '../../config/rabbitMqueue.js';



export const ingestFileService = async (userId, file) => {
    // 1. Increment user's usage quota in DB
    const user = await User.findByPk(userId);

    if (user.tier =='free' && user.requests_this_month>=user.max_requests){
        throw new Error("Monthly quota exceeded")
    }

    user.requests_this_month = user.requests_this_month + 1;
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

    if (user.tier == "free" && user.requests_this_month >= user.max_requests){
        throw new Error("Monthly quota exceeded");
    }

    user.requests_this_month = user.requests_this_month + 1;
    await user.save()

    // 2. Drop the question + context into RabbitMQ
    const queue = await getQueueChannel();
     const queryTicket = {
        userId : user.id,
        question : question,
        context : localContext
     }

     queue.sendToQueue("query_jobs",Buffer.from(JSON.stringify(queryTicket)),{ persistent:true})

    // 3. Return a success message
    return {
        message : "Query added to queue Successfully",
        status:"processing"
    }
}

