<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { X } from '@lucide/vue'
import ScenePlayer from './ScenePlayer.vue'
import type { Block } from '../types'
defineProps<{block:Block}>()
const emit=defineEmits<{close:[]}>()
const dialog=ref<HTMLDialogElement|null>(null)
onMounted(()=>dialog.value?.showModal())
onBeforeUnmount(()=>dialog.value?.close())
function backdrop(event:MouseEvent){if(event.target===dialog.value)dialog.value?.close()}
</script>
<template>
  <Teleport to="body">
    <dialog ref="dialog" class="scene-dialog" aria-label="知识演示窗口" @close="emit('close')" @click="backdrop">
      <div class="scene-dialog-content">
        <header><h2>{{block.title||'知识演示'}}</h2><button class="icon-btn" autofocus aria-label="关闭演示窗口" @click="dialog?.close()"><X :size="20"/></button></header>
        <ScenePlayer v-if="block.scene" :scene="block.scene"/>
      </div>
    </dialog>
  </Teleport>
</template>
<style scoped>
.scene-dialog{width:min(1180px,calc(100vw - 32px));max-width:none;max-height:calc(100dvh - 32px);padding:0;border:1px solid #d3ddce;border-radius:18px;background:#f7f9f5;color:#263c32;box-shadow:0 18px 80px #15241e40;overflow:auto}.scene-dialog::backdrop{background:#172a22a6}.scene-dialog-content{padding:18px}.scene-dialog-content>header{display:flex;align-items:center;justify-content:space-between;gap:15px;padding:0 4px 12px}.scene-dialog h2{font-size:18px;line-height:1.5;margin:0}.scene-dialog :deep(.scene-player){margin:0}.scene-dialog :deep(.scene-canvas svg){max-height:30dvh}.scene-dialog :deep(.scene-details){max-height:110px}.scene-dialog :deep(.scene-caption){min-height:0;padding:12px 22px}.scene-dialog :deep(.scene-player header){padding:12px 22px}@media(max-width:600px){.scene-dialog-content{padding:10px}.scene-dialog h2{font-size:15px}.scene-dialog :deep(.scene-canvas svg){min-width:400px}}
</style>
