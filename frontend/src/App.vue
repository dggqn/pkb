<script setup lang="ts">
import { ref } from "vue";
import ConversationView from "./components/ConversationView.vue";
type Theme = "day" | "night" | "garden";
const theme = ref<Theme>("night");
const themes: [Theme, string][] = [
  ["day", "白昼"],
  ["night", "夜航"],
  ["garden", "林间"],
];
const comets = ref<
  {
    id: number;
    left: string;
    top: string;
    size: string;
    duration: string;
    delay: string;
    direction?: string;
    angle?: string;
  }[]
>([]);
const blades = Array.from({ length: 110 }, (_, i) => {
  const x = (((i * 47) % 997) / 997) * 1440;
  const seed = (i * 7919) % 101;
  const y = 365 + Math.sin(x / 170) * 38 + (seed % 85);
  const h = 28 + (seed % 42);
  return {
    x,
    y,
    h,
    lean: (seed % 12) - 6,
    duration: 3.8 + (seed % 19) / 10,
    delay: -((seed % 40) / 10),
    color: ["#71844f", "#84945f", "#9ca676", "#62784a", "#b2b58a"][seed % 5],
  };
});
let previousCometSide: 0 | 1 = 1;
function seedComets() {
  previousCometSide = previousCometSide === 0 ? 1 : 0;
  const x =
    previousCometSide === 0
      ? Math.floor(Math.random() * 500) / 10
      : 50 + Math.floor(Math.random() * 501) / 10;
  const angle = x < 50 ? 35 + Math.random() * 20 : 125 + Math.random() * 20;
  const travel = (x < 50 ? 1 : -1) * (36 + Math.random() * 24);
  comets.value = [
    {
      id: Date.now(),
      left: x + "%",
      top: "0%",
      size: 5 + Math.random() * 3 + "px",
      duration: 3.8 + Math.random() * 1.6 + "s",
      delay: "0s",
      direction: travel + "vw",
      angle: angle + "deg",
    },
  ];
}
function setTheme(value: Theme) {
  theme.value = value;
  if (value === "night") seedComets();
}
</script>
<template>
  <main
    class="app"
    :data-theme="theme">
    <div
      class="ambient"
      aria-hidden="true">
      <i class="orb orb-a"></i><i class="orb orb-b"></i>
      <div class="stars"></div>
      <div class="star-shapes">
        <i>✦</i><i>✧</i><i>✦</i><i>✧</i><i>✦</i><i>✧</i><i>✦</i><i>✧</i>
      </div>
      <div class="horizon"></div>
      <svg
        class="bamboo-shadow"
        viewBox="0 0 1680 950"
        preserveAspectRatio="none">
        <g class="spray spray-left">
          <path
            class="branch"
            d="M-20 490Q170 310 350 170T620 -40" />
          <path
            class="branch"
            d="M40 760Q120 550 230 385T430 40" />
          <path
            class="branch"
            d="M80 300Q280 250 470 120T760 -20" />
          <path
            class="branch"
            d="M-10 560Q180 470 340 345T590 170" />
          <path
            class="leaf"
            d="M230 297Q112 184 87 85Q173 154 230 297Z" />
          <path
            class="leaf"
            d="M236 293Q219 145 273 35Q279 168 236 293Z" />
          <path
            class="leaf"
            d="M244 290Q373 161 478 142Q381 238 244 290Z" />
          <path
            class="leaf"
            d="M343 193Q267 75 278 -13Q344 68 343 193Z" />
          <path
            class="leaf"
            d="M349 192Q391 77 469 19Q424 119 349 192Z" />
          <path
            class="leaf"
            d="M170 455Q48 394 6 308Q91 350 170 455Z" />
          <path
            class="leaf"
            d="M174 449Q189 329 256 263Q222 373 174 449Z" />
          <path
            class="leaf"
            d="M183 452Q308 370 405 369Q309 425 183 452Z" />
          <path
            class="leaf"
            d="M105 637Q20 552 15 472Q74 531 105 637Z" />
          <path
            class="leaf"
            d="M109 634Q145 523 220 472Q172 562 109 634Z" />
          <path
            class="leaf"
            d="M124 642Q251 580 343 599Q240 638 124 642Z" />
          <path
            class="leaf"
            d="M432 178Q358 87 366 18Q421 77 432 178Z" />
          <path
            class="leaf"
            d="M438 177Q490 78 563 42Q516 123 438 177Z" />
        </g>
        <g class="spray spray-top">
          <path
            class="branch"
            d="M610 -40Q810 120 990 205T1300 240" />
          <path
            class="leaf"
            d="M800 112Q709 38 686 -35Q758 4 800 112Z" />
          <path
            class="leaf"
            d="M810 118Q821 18 876 -25Q858 59 810 118Z" />
          <path
            class="leaf"
            d="M824 124Q925 44 1000 46Q925 101 824 124Z" />
          <path
            class="leaf"
            d="M1053 218Q976 139 969 69Q1022 130 1053 218Z" />
          <path
            class="leaf"
            d="M1061 219Q1102 116 1169 75Q1134 164 1061 219Z" />
          <path
            class="leaf"
            d="M1074 224Q1181 165 1262 180Q1174 211 1074 224Z" />
        </g>
        <g class="spray spray-right">
          <path
            class="branch"
            d="M1660 -20Q1550 155 1480 340T1410 620" />
          <path
            class="leaf"
            d="M1550 166Q1451 107 1432 35Q1498 75 1550 166Z" />
          <path
            class="leaf"
            d="M1559 165Q1584 71 1644 28Q1615 109 1559 165Z" />
          <path
            class="leaf"
            d="M1511 301Q1426 246 1402 180Q1467 217 1511 301Z" />
          <path
            class="leaf"
            d="M1517 298Q1551 210 1613 180Q1572 253 1517 298Z" />
        </g>
      </svg>
      <div class="sea">
        <i></i><i></i><i></i><b></b
        ><svg
          class="sailboat"
          viewBox="0 0 120 90">
          <path
            class="mast"
            d="M59 18v48" />
          <path
            class="sail"
            d="M55 25 30 59h25zM63 32l22 27H63z" />
          <path
            class="boat"
            d="M22 67h77l-13 12H38z" />
          <circle
            class="person"
            cx="46"
            cy="54"
            r="3" />
          <path
            class="person"
            d="M46 57v8m-5-4h10" />
        </svg>
      </div>
      <i
        v-for="comet in comets"
        :key="comet.id"
        class="meteor"
        :style="{
          left: comet.left,
          top: comet.top,
          '--comet-size': comet.size,
          '--comet-duration': comet.duration,
          '--comet-delay': comet.delay,
          '--comet-travel': comet.direction,
          '--comet-angle': comet.angle,
        }"
        @animationend="theme === 'night' && seedComets()"></i>
      <div class="garden-scene">
        <svg
          viewBox="0 0 1440 520"
          preserveAspectRatio="none">
          <path
            class="far-hill"
            d="M0 265Q200 175 390 245T790 224q230-100 650 12v284H0Z" />
          <path
            class="near-hill"
            d="M0 350q190-130 400-35t405-18q270-145 635-15v238H0Z" />
          <path
            class="front-hill"
            d="M0 415q210-94 450-22t472-35q237-91 518-14v176H0Z" />
          <g class="grass">
            <path
              v-for="(g, i) in blades"
              :key="i"
              :d="`M ${g.x - 2} ${g.y} Q ${g.x + g.lean - 4} ${g.y - g.h * 0.6} ${g.x + g.lean * 1.5} ${g.y - g.h} Q ${g.x + g.lean + 5} ${g.y - g.h * 0.58} ${g.x + 2} ${g.y} Z`"
              :style="{
                transformOrigin: `${g.x}px ${g.y}px`,
                animationDuration: `${g.duration}s`,
                animationDelay: `${g.delay}s`,
                stroke: g.color,
              }" />
          </g>
        </svg>
      </div>
    </div>
    <header class="header">
      <a class="brand"
        ><span class="sigil"
          ><svg viewBox="0 0 40 40">
            <path d="M10 12h20M10 20h13M10 28h17" />
            <circle
              cx="27"
              cy="20"
              r="3" /></svg></span
        ><span>知间</span></a
      >
      <div
        class="theme-switch"
        role="group"
        aria-label="选择主题">
        <button
          v-for="[id, label] in themes"
          :key="id"
          :class="{ active: theme === id }"
          @click="setTheme(id)">
          <span class="theme-icon">{{
            id === "day" ? "☼" : id === "night" ? "✦" : "❋"
          }}</span
          >{{ label }}
        </button>
      </div>
      <div class="library"><span></span>个人知识对话</div>
    </header>
    <ConversationView />
    <footer>你的记录，只属于你 <span>·</span> 知识在这里生长</footer>
  </main>
</template>
