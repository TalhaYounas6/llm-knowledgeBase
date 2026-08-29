import asyncHandler from "express-async-handler";
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { User } = require("../models/index.cjs");

 export const protect = asyncHandler(async(req,res,next)=>{

    let token;

    if(req.headers.authorization && req.headers.authorization.startsWith('Bearer')){
        try {

            token = req.headers.authorization.split(" ")[1];

            const user = await User.findOne({where:{api_key:token},raw:true});

        if(!user){
            const error = new Error("No token provided");
            error.statusCode = 401;
            throw error;
        }

         req.user = user;
         next();
            
        } catch (error) {
            error.statusCode = 401
            throw error;
        }
        
    }

        if(!token){
            const error = new Error("No token provided");
            error.statusCode = 401;
            throw error;
        } 
 })

 export const protectWorker = asyncHandler(async(req,res,next)=>{
    if(req.headers["x-worker-secret"] && req.headers["x-worker-secret"] == process.env.WORKER_SECRET){
        next();
    }
    else{
        return res.status(401).json({"message" : "Not authorized for this action"});
    }
 })