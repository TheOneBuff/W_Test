import { AndroidAgent, AndroidDevice, getConnectedDevices } from '@midscene/android';
import fs from 'fs';
import path from 'path';

// 获取命令行参数
const scriptPath = process.argv[2];
const reportOutputPath = process.argv[3];

if (!scriptPath) {
    console.error("Usage: npx tsx runner.ts <script.json> <output_report.html>");
    process.exit(1);
}

(async () => {
  try {
    // 1. 读取步骤
    const scriptRaw = fs.readFileSync(scriptPath, 'utf-8');
    const instructions: string[] = JSON.parse(scriptRaw);

    console.log(`Loaded ${instructions.length} steps.`);

    // 2. 连接设备
    const devices = await getConnectedDevices();
    if (devices.length === 0) {
        throw new Error("No Android device connected via ADB.");
    }
    console.log(`Connecting to device: ${devices[0].udid}`);

    const device = new AndroidDevice(devices[0].udid);
    await device.connect();

    // 3. 初始化 Agent
    // 注意: Midscene 通常会自动生成报告。我们需要查看文档或源码确认如何指定路径。
    // 假设它在当前目录生成 ./midscene_run/report/index.html，我们最后手动移动它。
    const agent = new AndroidAgent(device);

    // 4. 执行
    for (const step of instructions) {
        console.log(`> Action: ${step}`);
        // 可以在这里加 try-catch 来保证单步失败不直接退出，而是记录错误
        await agent.aiAct(step);
    }

    console.log("Execution finished.");

    // 5. 处理报告 (Mock逻辑，实际需根据 Midscene 生成逻辑调整)
    // 假设 Midscene 默认生成在 ./midscene_run/report/index.html
    const defaultReportDir = path.join(process.cwd(), 'midscene_run', 'report');
    const defaultReportFile = path.join(defaultReportDir, 'index.html');

    // 如果 Midscene 还没生成文件，我们可能需要手动调用生成报告的方法(如有)
    // 或者等待文件刷写
    await new Promise(r => setTimeout(r, 1000));

    if (fs.existsSync(defaultReportFile) && reportOutputPath) {
        fs.copyFileSync(defaultReportFile, reportOutputPath);
        console.log(`Report copied to ${reportOutputPath}`);
    } else if (reportOutputPath) {
        // 如果没有生成报告，创建一个简单的 HTML 占位
        fs.writeFileSync(reportOutputPath, "<html><body><h1>Execution Finished</h1><p>No Midscene report generated.</p></body></html>");
    }

    process.exit(0);

  } catch (e) {
    console.error("Fatal Error:", e);

    // 发生错误也尝试写入一个错误报告
    if (reportOutputPath) {
         fs.writeFileSync(reportOutputPath, `<html><body><h1>Execution Failed</h1><pre>${e}</pre></body></html>`);
    }
    process.exit(1);
  }
})();