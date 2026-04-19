import amqp from "amqplib"

let channel = null;

export const getQueueChannel = async ()=>{
    if(channel) return channel;

    try {

        const connection = amqp.connect(process.env.QUEUE_URL);
        channel = await connection.createChannel();

        await channel.assertQueue("pdf_jobs",{durable:true});
        await channel.assertQueue("query_jobs",{durable:true});

        console.log("Connected to rabbit queue.")

        return channel;
        
    } catch (error) {
        console.error("Error connecting to rabbit queue: ",error);
        throw new Error("Message Queue Is Currently Unavailable");
    }

}