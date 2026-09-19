import { Queue } from "bullmq";
import IORedis from "ioredis";

export const QUEUE_NAME = "deck-generation";

const REDIS_URL = process.env.REDIS_URL || "redis://localhost:6379";

declare global {
  // eslint-disable-next-line no-var
  var __deckQueue: Queue | undefined;
  // eslint-disable-next-line no-var
  var __deckQueueConnection: IORedis | undefined;
}

function getConnection(): IORedis {
  if (!global.__deckQueueConnection) {
    global.__deckQueueConnection = new IORedis(REDIS_URL, {
      maxRetriesPerRequest: null,
    });
  }
  return global.__deckQueueConnection;
}

export function getDeckQueue(): Queue {
  if (!global.__deckQueue) {
    global.__deckQueue = new Queue(QUEUE_NAME, { connection: getConnection() });
  }
  return global.__deckQueue;
}
