import { GoogleGenerativeAI } from "@google/generative-ai";

export const chatAi = (api_key)=>{
    const genAI = new GoogleGenerativeAI(api_key);
    const model = genAI.getGenerativeModel({ model: "gemini-2.5-flash" });
    return model;
}