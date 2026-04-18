import asyncio
from utils.mimo_engine import MiMoEngine

async def test():
    engine = MiMoEngine()
    print("Generating speech...")
    audio_bytes = await engine.generate_speech("Hello world", "mimo_default")
    if audio_bytes:
        print(f"Success! Audio size: {len(audio_bytes)} bytes")
        print(f"Header: {audio_bytes[:10]}")
    else:
        print("Failed to get audio bytes.")

if __name__ == "__main__":
    asyncio.run(test())
