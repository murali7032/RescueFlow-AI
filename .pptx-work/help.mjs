import { FileBlob, PresentationFile } from '@oai/artifact-tool';
const p = await PresentationFile.importPptx(await FileBlob.load('C:/Users/MKREDDY/Downloads/Submission Template _ AI Builder Cup.pptx'));
for (const query of ['image.delete', 'slide.shapes.delete', 'slides.delete', 'slide text style']) {
  console.log(query, p.help('*', { search: query, include: ['index','examples','notes'], maxChars: 2500 }).ndjson);
}
