import { createRequire } from 'module';
import bcrypt, { genSalt } from "bcrypt";
const require = createRequire(import.meta.url);
const {User} = require("../../models/index.cjs");


export const registerUser = async(username,email,password,customLLMKey=null)=>{
    const user = await User.findOne({where : {email}, raw:true})
    if(user){
       throw new Error("User already exists")
    }

    const salt = await bcrypt.genSalt(12);
    const hashedPassword = await bcrypt.hash(password,salt);

    let encryptedKey = null;
    if (customLLMKey) {
        // will write an encrypt() function later using Node's  crypto module
        // encryptedKey = encrypt(customLLMKey); 
    }


    const newUser = await User.create({username,email,password_hash:hashedPassword,encrypted_custom_key: encryptedKey});
    

    return newUser;
}