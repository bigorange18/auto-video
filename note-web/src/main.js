import { createApp } from 'vue'
import './style.css'
import App from './App.vue'

createApp(App).mount('#app')

// const button=document.querySelector("button");
// button.addEventListener("click", updateName);

// function updateName() {
//     const name = prompt("Please enter your name:");
//     button.textContent = `Player 1: ${name}`;
// }

// document.addEventListener("button", () => {
//   function createParagraph() {
//     const para = document.createElement("p");
//     para.textContent = "你点击了按钮！";
//     document.body.appendChild(para);
//   }

//   const buttons = document.querySelectorAll("button");

//   for (const button of buttons) {
//     button.addEventListener("click", createParagraph);
//   }
// });

function createParagraph() {
  const para = document.createElement("p");
  para.textContent = "你点击了按钮！";
  document.body.appendChild(para);
}

const buttons = document.querySelectorAll("button");

for (const button of buttons) {
  button.addEventListener("click", createParagraph);
}