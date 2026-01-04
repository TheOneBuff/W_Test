<template>
  <div class="dashboard-container">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>总任务数</template>
          <div class="card-num">120</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>成功率</template>
          <div class="card-num" style="color: #67C23A">98%</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 20px; height: 400px;">
      <el-empty description="图表开发中..." />
    </el-card>
  </div>
</template>

<style scoped>
.card-num { font-size: 24px; font-weight: bold; text-align: center; }
</style>
