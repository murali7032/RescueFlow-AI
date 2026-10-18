import { FileBlob, PresentationFile } from '@oai/artifact-tool';
const p = await PresentationFile.importPptx(await FileBlob.load('C:/Users/MKREDDY/Downloads/Submission Template _ AI Builder Cup.pptx'));
const result = await p.inspect({select:'$.slides[1]',include:['id','index','layout','elements.id','elements.kind','elements.text','elements.position','elements.style','elements.alt']});
console.log(result.ndjson);
