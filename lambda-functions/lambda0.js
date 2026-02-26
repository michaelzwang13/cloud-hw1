import { LexRuntimeV2Client, RecognizeTextCommand } from "@aws-sdk/client-lex-runtime-v2";

const client = new LexRuntimeV2Client({ region: 'us-east-1' });

const BOT_ID = 'NVBMODY8ST';
const BOT_ALIAS_ID = 'TSTALIASID';
const LOCALE_ID = 'en_US';

export const handler = async (event) => {
  const body = JSON.parse(event.body || '{}');
  const userMessage = body.messages?.[0]?.unstructured?.text;

  if (!userMessage) {
    return {
      statusCode: 400,
      headers: { "Access-Control-Allow-Origin": "*", "Content-Type": "application/json" },
      body: JSON.stringify({ error: 'No message provided' })
    };
  }

  const sessionId = event.requestContext?.identity?.sourceIp || 'default-session';

  const command = new RecognizeTextCommand({
    botId: BOT_ID,
    botAliasId: BOT_ALIAS_ID,
    localeId: LOCALE_ID,
    sessionId,
    text: userMessage
  });

  const lexResponse = await client.send(command);

  const messages = (lexResponse.messages || []).map((msg, i) => ({
    type: 'unstructured',
    unstructured: {
      id: String(i),
      text: msg.content,
      timestamp: new Date().toISOString()
    }
  }));

  return {
    statusCode: 200,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ messages })
  };
};