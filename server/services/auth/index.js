import { createRequire } from 'module';
import bcrypt, { genSalt } from "bcrypt";
import { encrypt } from '../../utils/crypto.js';
const require = createRequire(import.meta.url);
const {User} = require("../../models/index.cjs");


export const registerUser = async(username,email,password,customLLMKey)=>{
    const user = await User.findOne({where : {email}, raw:true})
    if(user){
       throw new Error("User already exists")
    }

    const salt = await bcrypt.genSalt(12);
    const hashedPassword = await bcrypt.hash(password,salt);

    let encryptedKey = null;
    if (customLLMKey) {
        
        encryptedKey = encrypt(customLLMKey);
    }


    const newUser = await User.create({username,email,password_hash:hashedPassword,encrypted_custom_key: encryptedKey});
    

    return newUser;
}

export const loginUser = async(email,password)=>{
    const user = await User.findOne({where: {email},raw:true});

    if(!user){
        throw new Error("Invalid Email or Password!");
    }

    const isMatch = await bcrypt.compare(password,user.password_hash);

    if(isMatch){
        return user;
    }else{
        throw new Error("Invalid email or password");
    }

}