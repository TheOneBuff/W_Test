import { AndroidAgent, AndroidDevice, getConnectedDevices } from '@midscene/android';
import fs from 'fs';

(async () => {
  try {
    // 1. 读取任务脚本
    const scriptRaw = fs.readFileSync('temp_script.json', 'utf-8');
    let instructions: string[] = [];

    try {
        // 尝试解析 JSON 数组
        instructions = JSON.parse(scriptRaw);
    } catch {
        // 如果不是 JSON，按行分割纯文本
        instructions = scriptRaw.split('\n').filter(line => line.trim() !== '');
    }

    // 2. 连接设备
    const devices = await getConnectedDevices();
    if (devices.length === 0) throw new Error("No device connected");

    const device = new AndroidDevice(devices[0].udid);
    await device.connect();

    // 3. 初始化 Agent
    const agent = new AndroidAgent(device);

    // 4. 执行步骤
    for (const step of instructions) {
        console.log(`> Executing: ${step}`);
        await agent.aiAct(step);
    }

    console.log("Task Completed.");
    process.exit(0);

  } catch (e) {
    console.error("Execution Failed:", e);
    process.exit(1);
  }
})();
