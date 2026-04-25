import { createRequire } from 'module';
import { encrypt } from '../../utils/crypto.js';
const require = createRequire(import.meta.url);
const { User } = require("../../models/index.cjs");

export const getUserStatus = async (userId) => {
    const user = await User.findByPk(userId, { raw: true });
    
    if (!user) {
        throw new Error("User not found");
    }

    return {
        username: user.username,
        tier: user.tier,
        usage: `${user.requests_today} / ${user.daily_limit}`
    };
}

export const changeApiKey = async(userId,customKey)=>{
    const user = await User.findByPk(userId,{raw:true});
    if (!user) {
        throw new Error("User not found");
    }

    user.encrypted_custom_key = encrypt(customKey);

    user.tier = "byok";

    await user.save();

    return { message : "CUSTOM API KEY changed SUCCESSFULLY"};
}