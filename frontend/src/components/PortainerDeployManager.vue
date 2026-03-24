<template>
  <DeployTaskManager mode="portainer" />
</template>

<script>
import DeployTaskManager from "./DeployTaskManager.vue";

export default {
  name: "PortainerDeployManager",
  components: {
    DeployTaskManager,
  },
};
</script>
