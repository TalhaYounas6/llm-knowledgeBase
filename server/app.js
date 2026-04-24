import express from "express";
import cors from "cors";
import "dotenv/config";
import { globalErrorHandler } from "./middlewares/errorHandling.middleware.js";



const app = express();


app.use(cors());

app.use(express.json());

app.get("/", (req, res) => {
  res.send("server is live");
});

app.use(globalErrorHandler)


export default app;

