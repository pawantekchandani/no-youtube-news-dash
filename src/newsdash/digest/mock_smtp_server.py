import asyncio
import logging
import os
from datetime import datetime

# Setup logging to both stdout and a log file
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/mock_smtp.log")
    ]
)
logger = logging.getLogger("MockSMTPServer")

async def handle_client(reader, writer):
    peer = writer.get_extra_info('peername')
    logger.info(f"Connection accepted from {peer}")
    
    writer.write(b"220 localhost ESMTP MockServer\r\n")
    await writer.drain()
    
    email_data = []
    in_data = False
    
    while True:
        try:
            data = await reader.readline()
            if not data:
                break
            
            line = data.decode('utf-8', errors='ignore')
            
            if in_data:
                # In SMTP, a single dot on a line by itself marks the end of the mail data
                if line == ".\r\n" or line == ".\n":
                    in_data = False
                    raw_email = "".join(email_data)
                    logger.info("=== RECEIVED EMAIL CONTENT ===")
                    print(raw_email)
                    logger.info("==============================")
                    writer.write(b"250 2.0.0 Ok: queued as mock-msg-12345\r\n")
                    await writer.drain()
                    email_data = []
                else:
                    email_data.append(line)
            else:
                cmd = line.strip().upper()
                if cmd.startswith("QUIT"):
                    writer.write(b"221 2.0.0 Bye\r\n")
                    await writer.drain()
                    break
                elif cmd.startswith("EHLO") or cmd.startswith("HELO"):
                    writer.write(b"250-localhost Hello\r\n250-SIZE 25000000\r\n250 HELP\r\n")
                elif cmd.startswith("MAIL FROM:"):
                    writer.write(b"250 2.1.0 Ok\r\n")
                elif cmd.startswith("RCPT TO:"):
                    writer.write(b"250 2.1.5 Ok\r\n")
                elif cmd.startswith("DATA"):
                    in_data = True
                    writer.write(b"354 Start mail input; end with <CR><LF>.<CR><LF>\r\n")
                elif cmd == "":
                    # Empty command, ignore
                    pass
                else:
                    writer.write(b"250 Ok\r\n")
                await writer.drain()
        except Exception as e:
            logger.error(f"Error handling connection: {e}")
            break
            
    writer.close()
    await writer.wait_closed()
    logger.info(f"Connection closed for {peer}")

async def main():
    host = "127.0.0.1"
    port = 1025
    server = await asyncio.start_server(handle_client, host, port)
    logger.info(f"Mock SMTP server listening on {host}:{port}...")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutting down.")
