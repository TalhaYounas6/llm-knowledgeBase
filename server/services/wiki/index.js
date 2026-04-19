import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { User, IngestJob } = require("../../models/index.cjs");
import { getQueueChannel } from '../../config/rabbitMqueue';




export const ingestFileService = async (userId, file) => {
    // 1. Increment user's usage quota in DB
    // 2. Add job to IngestJobs table (status: 'pending')
    // 3. Talk to RabbitMQ (Send ticket with file.path and job.id)
    // 4. Return job details so the Controller can send a 202 response
}

export const queryWikiService = async (userId, question, localContext) => {
    // 1. Increment user's usage quota
    // 2. Drop the question + context into RabbitMQ
    // 3. Return a success message
}

