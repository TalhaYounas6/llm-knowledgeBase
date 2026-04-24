import express from "express";
import cors from "cors";
import "dotenv/config";
import { globalErrorHandler } from "./middlewares/errorHandling.middleware.js";

import authRoutes from "./routes/auth/index.js";
import userRoutes from "./routes/user/index.js";
import wikiRoutes from "./routes/wiki/index.js";


const app = express();


app.use(cors());

app.use(express.json());

app.get("/", (req, res) => {
  res.send("server is live");
});

app.use(authRoutes);
app.use(userRoutes);
app.use(wikiRoutes);


app.use(globalErrorHandler);


export default app;

