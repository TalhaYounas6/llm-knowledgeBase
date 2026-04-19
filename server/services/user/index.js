import { createRequire } from 'module';
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
        usage: `${user.requests_this_month} / ${user.max_requests}`
    };
}