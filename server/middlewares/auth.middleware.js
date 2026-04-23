import asyncHandler from "express-async-handler";
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const { User } = require("../../models/index.cjs");

 export const protect = asyncHandler(async(req,res,next)=>{

    let token;

    if(req.headers.authorization && req.headers.authorization.startswith('Bearer')){
        try {

            token = req.headers.authorization.split(" ")[1];

        const user = await User.findOne({where:{api_key:token},raw:true});

        if(!user){
            res.status(401);
            throw new Error("Not authorized!")
        }

         req.user = user;
         next();
            
        } catch (error) {
            res.status(401);
            throw new Error("Not authorized, token failed");
        }
        
    }

        if(!token){
            res.status(401);
            throw new Error("Not token provided!")
        } 
 })