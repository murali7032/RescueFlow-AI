import { FileBlob, PresentationFile } from '@oai/artifact-tool';
const p = await PresentationFile.importPptx(await FileBlob.load('C:/Users/MKREDDY/Downloads/Submission Template _ AI Builder Cup.pptx'));
console.log('slideSize', JSON.stringify(p.slideSize));
for (const idx of [0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]) {
  const slide = p.slides.items[idx];
  const result = await p.inspect({select: `$.slides[${idx}]`, include: ['id','index','layout','elements.id','elements.kind','elements.text','elements.position','elements.style']});
  console.log(`SLIDE ${idx+1}\n${result.ndjson}`);
}
