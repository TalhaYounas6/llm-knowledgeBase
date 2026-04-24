import asyncHandler from "express-async-handler";
import { registerUser } from "../../services/auth/index.js";

export const registerController = asyncHandler(async(req,res)=>{
    const {username,email,password,customLLMKey} = req.body;

    if(!username||!password||!email){
        const error = new Error("Missing Credentials!")
        error.statusCode = 400
        return next(error);
    }

    const newUser = await registerUser(username,email,password,customLLMKey);

    res.status(201).json({
        message : "User registered successfully",
        apiKey : newUser.api_key
    })
})