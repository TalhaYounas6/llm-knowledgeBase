import asyncHandler from "express-async-handler";
import { registerUser,loginUser } from "../../services/auth/index.js";

export const registerController = asyncHandler(async(req,res)=>{
    const {username,email,password,customLLMKey} = req.body;

    if(!username||!password||!email){
        const error = new Error("Missing Credentials!")
        error.statusCode = 400
        throw error;
    }

    const newUser = await registerUser(username,email,password,customLLMKey);

    res.status(201).json({
        message : "User registered successfully",
        apiKey : newUser.api_key
    })
})

export const loginController = asyncHandler(async (req, res) => {
    const { email, password } = req.body;

    if (!email || !password) {
        const error = new Error("Enter email and password");
        error.statusCode = 400;
        throw error;
    }

    const user = await loginUser(email, password);

    res.status(200).json({
        message: "Login successful",
        apiKey: user.api_key 
    });
});