// Chart.js (MIT) keeps its licence line at the top of the file that carries it (the minifier drops comments).
const LINE = '/*! Chart.js v4.5.1 | https://www.chartjs.org | (c) 2025 Chart.js Contributors | Released under the MIT License */'

export function chartjsLicence() {
  return {
    name: 'chartjs-licence',
    generateBundle(_, bundle) {
      for (const chunk of Object.values(bundle)) {
        if (chunk.type === 'chunk' && /chart-draw|agui-chat\.charts/.test(chunk.fileName)) chunk.code = `${LINE}\n${chunk.code}`
      }
    },
  }
}
