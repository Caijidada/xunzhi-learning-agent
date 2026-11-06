import { ref, watch } from 'vue'

export function usePanels(){
  const leftCollapsed=ref(localStorage.getItem('xunzhi.leftCollapsed')==='true'||window.innerWidth<1000)
  const rightCollapsed=ref(localStorage.getItem('xunzhi.rightCollapsed')==='true')
  const rightWidth=ref(Math.max(280,Math.min(600,Number(localStorage.getItem('xunzhi.rightWidth'))||348)))
  watch(leftCollapsed,v=>localStorage.setItem('xunzhi.leftCollapsed',String(v)))
  watch(rightCollapsed,v=>localStorage.setItem('xunzhi.rightCollapsed',String(v)))
  watch(rightWidth,v=>localStorage.setItem('xunzhi.rightWidth',String(v)))
  let dragging=false,startX=0,startWidth=0
  function resizeStart(e:PointerEvent){dragging=true;startX=e.clientX;startWidth=rightWidth.value;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);e.preventDefault()}
  function resizeMove(e:PointerEvent){if(dragging)rightWidth.value=Math.max(280,Math.min(Math.min(650,window.innerWidth*.55),startWidth+startX-e.clientX))}
  function resizeEnd(){dragging=false}
  function resizeKey(e:KeyboardEvent){if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();rightWidth.value=Math.max(280,Math.min(650,rightWidth.value+(e.key==='ArrowLeft'?20:-20)))}}
  return {leftCollapsed,rightCollapsed,rightWidth,resizeStart,resizeMove,resizeEnd,resizeKey}
}
