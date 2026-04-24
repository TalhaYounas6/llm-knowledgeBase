export const globalErrorHandler = (err,req,res,next)=>{
    res.status(err.statusCode || 500).json({
        message: err.message,
        stack: process.env.NODE_ENV === "production" ? null : err.stack
    });
}