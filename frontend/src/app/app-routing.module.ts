import { NgModule } from "@angular/core";
import { Routes, RouterModule, UrlSegment, ExtraOptions } from "@angular/router";

import { ImageDetailComponent } from "./image-detail/image-detail.component";
import { ImageListComponent } from "./image-list/image-list.component";
import { ImageLoaderComponent } from "./image-loader/image-loader.component";
import { NotFoundComponent } from "./not-found/not-found.component";


const routes: Routes = [
  {
    path: "",
    component: ImageLoaderComponent,
  },
  {
    matcher: (url) => {
      if (
        url.length === 2
        && url[0].path === "images"
        && url[1].path.match(/^[0-9a-f]{6}$/)
      ) {
        return {
          consumed: url,
          posParams: {
            color: new UrlSegment(url[1].path, {})
          }
        };
      }      return null;
    },
    component: ImageListComponent,
  },
  {
    path: "**",
    component: NotFoundComponent
  }
];


const routerOptions: ExtraOptions = {
  useHash: false,
  anchorScrolling: 'enabled',
};

@NgModule({
  imports: [RouterModule.forRoot(routes, routerOptions)],
  exports: [RouterModule]
})
export class AppRoutingModule { }

export const routingComponents = [
  ImageDetailComponent,
  ImageListComponent,
  ImageLoaderComponent,
  NotFoundComponent
];
